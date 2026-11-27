#pragma once

// API na Vercel (sem https://)
const char* API_HOST    = "tam-omega-silk.vercel.app";
const char* API_CAMINHO = "/api/sensores";

// pinos
const int SENSOR       = A0;
const int BOTAO        = 2;
const int LED_VERDE    = 3;
const int LED_VERMELHO = 4;
const int RELE         = 5;

// se o relé funcionar ao contrário é só trocar estes dois
const int RELE_LIGADO    = HIGH;
const int RELE_DESLIGADO = LOW;

// acima disto a ventoinha liga
const float LIMITE_TEMPERATURA = 24.0;

// de quanto em quanto tempo lê e envia (5 segundos)
const unsigned long INTERVALO_LEITURA = 5000UL;
const unsigned long INTERVALO_API     = 5000UL;

// número de leituras para fazer a média
const int NUMERO_LEITURAS = 50;

// para acertar com um termómetro a sério, se o arduino der 3 graus a mais põe-se -3.0
const float AJUSTE_TEMPERATURA = 0.0;