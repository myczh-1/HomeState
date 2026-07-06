package main

import (
	"flag"
	"fmt"
	"log"
	"net/http"
	"os"
	"os/signal"
	"syscall"
	"time"

	"github.com/huanghe/HomeState/internal/api"
	"github.com/huanghe/HomeState/internal/config"
	"github.com/huanghe/HomeState/internal/context"
	"github.com/huanghe/HomeState/internal/decision"
	"github.com/huanghe/HomeState/internal/facts"
	"github.com/huanghe/HomeState/internal/guardrails"
	"github.com/huanghe/HomeState/internal/haclient"
	"github.com/huanghe/HomeState/internal/hasensor"
	"github.com/huanghe/HomeState/internal/model"
	"github.com/huanghe/HomeState/internal/semantic"
)

func main() {
	cfgPath := flag.String("config", "config.json", "path to config file")
	flag.Parse()

	cfg, err := config.Load(*cfgPath)
	if err != nil {
		log.Fatalf("load config: %v", err)
	}
	log.Printf("[main] starting HomeState in %s mode", cfg.RunMode)

	// Initialize layers
	factStore := facts.New(10000)
	semRegistry := semantic.New()
	ctxEngine := context.New()
	guardEngine := guardrails.New()
	decEngine := decision.New(ctxEngine, guardEngine, semRegistry, cfg.RunModeEnum())

	// Load semantic mappings if file exists
	if err := semRegistry.LoadFile("semantics.json"); err != nil {
		if !os.IsNotExist(err) {
			log.Printf("[main] warn: load semantics: %v", err)
		}
	}

	// Connect to Home Assistant
	haClient := haclient.New(cfg.HAURL, cfg.HAToken)
	if err := haClient.Connect(); err != nil {
		log.Printf("[main] warn: HA connect failed: %v (running in offline mode)", err)
	} else {
		// Wire: HA event → facts → context
		haClient.OnEvent(func(ev model.FactEvent) {
			factStore.Record(ev)
			sem := semRegistry.Get(ev.EntityID)
			ctxEngine.ProcessFact(ev, sem)
		})

		if err := haClient.SubscribeEvents(); err != nil {
			log.Printf("[main] warn: subscribe events: %v", err)
		} else {
			go func() {
				if err := haClient.Listen(); err != nil {
					log.Printf("[main] HA listener error: %v", err)
				}
			}()
		}
	}

	// Start context tick loop (confidence decay, room timeout)
	stop := make(chan struct{})
	go func() {
		ticker := time.NewTicker(30 * time.Second)
		defer ticker.Stop()
		for {
			select {
			case <-ticker.C:
				ctxEngine.Tick()
			case <-stop:
				return
			}
		}
	}()

	// Start virtual sensor push loop
	if cfg.HAURL != "" && cfg.HAToken != "" {
		writer := hasensor.New(cfg.HAURL, cfg.HAToken, ctxEngine)
		go writer.RunPushLoop(10*time.Second, stop)
		log.Println("[main] virtual sensor push loop started")
	}

	// Start HTTP API
	srv := api.New(ctxEngine, factStore, semRegistry, decEngine)
	addr := fmt.Sprintf(":%d", cfg.APIPort)
	httpSrv := &http.Server{Addr: addr, Handler: srv.Handler()}
	go func() {
		log.Printf("[main] API listening on %s", addr)
		if err := httpSrv.ListenAndServe(); err != nil && err != http.ErrServerClosed {
			log.Fatalf("api server: %v", err)
		}
	}()

	// Graceful shutdown
	sig := make(chan os.Signal, 1)
	signal.Notify(sig, syscall.SIGINT, syscall.SIGTERM)
	<-sig
	log.Println("[main] shutting down...")
	close(stop)
	haClient.Close()
	httpSrv.Close()
	semRegistry.SaveFile("semantics.json")
	log.Println("[main] bye")
}
