
package com.example.myapplication2102026

import android.content.Intent
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.util.Log
import android.view.View
import android.widget.Button
import androidx.core.view.ViewCompat
import androidx.core.view.WindowInsetsCompat
import android.widget.TextView
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import org.json.JSONObject

class MainActivity2 : AppCompatActivity() {

    private lateinit var api: ApiManager
    private lateinit var token: String

    private lateinit var tvTitle: TextView
    private lateinit var tvTemperatura: TextView
    private lateinit var tvVentoinha: TextView
    private lateinit var tvModo: TextView
    private lateinit var tvLedVerde: TextView
    private lateinit var tvLedVermelho: TextView

    private lateinit var buttonFan: Button
    private lateinit var buttonStandby: Button
    private lateinit var buttonLogs: Button
    private lateinit var buttonSair: Button

    // Comando guardado na API (o que a app pediu).
    // true = a ventoinha pode ligar sozinha quando está calor (automático)
    // false = a ventoinha fica desligada pela app
    private var comandoVentoinhaLigada = true

    // Estado REAL da ventoinha, enviado pelo Arduino (Mokxi).
    private var ventoinhaLigadaReal = false

    // Standby: ventoinha desligada e os dois LEDs a piscar.
    private var standbyAtivo = false

    // Para não mandar dois pedidos ao mesmo tempo.
    private var pedidoEmCurso = false

    private val handler = Handler(Looper.getMainLooper())

    // De 10 em 10 segundos vamos buscar a temperatura e o estado.
    // (com 5 s a BD da escola dava "too many connections")
    private val updateInterval = 10000L

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main2)

        val root = findViewById<View>(R.id.main)

        val paddingEsquerda = root.paddingLeft
        val paddingTopo = root.paddingTop
        val paddingDireita = root.paddingRight
        val paddingFundo = root.paddingBottom

        ViewCompat.setOnApplyWindowInsetsListener(root) { view, insets ->

            val barras = insets.getInsets(
                WindowInsetsCompat.Type.systemBars()
            )

            view.setPadding(
                paddingEsquerda + barras.left,
                paddingTopo + barras.top,
                paddingDireita + barras.right,
                paddingFundo + barras.bottom
            )

            insets
        }

        token = intent.getStringExtra("Token") ?: ""
        api = ApiManager.getInstance(this)

        tvTitle = findViewById(R.id.tvTitle)
        tvTemperatura = findViewById(R.id.tvTemperatura)
        tvVentoinha = findViewById(R.id.tvVentoinha)
        tvModo = findViewById(R.id.tvModo)
        tvLedVerde = findViewById(R.id.tvLedVerde)
        tvLedVermelho = findViewById(R.id.tvLedVermelho)

        buttonFan = findViewById(R.id.buttonFan)
        buttonStandby = findViewById(R.id.buttonStandby)
        buttonLogs = findViewById(R.id.buttonLogs)
        buttonSair = findViewById(R.id.button)

        tvTitle.text = "Painel de controlo"

        atualizarInterface()

        buttonSair.setOnClickListener {
            finish()
        }

        // Abrir o histórico numa página separada.
        buttonLogs.setOnClickListener {
            val intent = Intent(this, HistoryActivity::class.java)
            intent.putExtra("Token", token)
            startActivity(intent)
        }

        // Ligar ou sair do standby (LEDs a piscar ao mesmo tempo no Mokxi).
        buttonStandby.setOnClickListener {
            val dados = JSONObject()
                .put("standby", !standbyAtivo)

            enviarAlteracao(dados)
        }

        // Ligar ou desligar a ventoinha. Agora funciona sempre
        // (já não depende do modo manual, que foi retirado).
        buttonFan.setOnClickListener {
            // Trocamos o COMANDO e não o estado real, porque o real
            // pode demorar uns segundos a mudar no Arduino.
            val dados = JSONObject()
                .put("fan_on", !comandoVentoinhaLigada)

            enviarAlteracao(dados)
        }

        if (token.isEmpty()) {
            Toast.makeText(
                this,
                "A sessão terminou. Inicia sessão novamente.",
                Toast.LENGTH_LONG
            ).show()

            finish()
        }
    }

    private fun enviarAlteracao(dados: JSONObject) {
        // Se ainda estamos à espera da resposta anterior, ignoramos o clique.
        if (pedidoEmCurso) {
            return
        }

        pedidoEmCurso = true

        api.setActuatorState(
            token = token,
            dados = dados,
            onSuccess = { resposta ->
                pedidoEmCurso = false

                atualizarEstado(resposta)

                Toast.makeText(
                    this,
                    "Comando enviado. O Mokxi aplica-o em poucos segundos.",
                    Toast.LENGTH_SHORT
                ).show()
            },
            onError = { erro ->
                pedidoEmCurso = false

                Toast.makeText(
                    this,
                    "Não foi possível atualizar o sistema: $erro",
                    Toast.LENGTH_LONG
                ).show()

                atualizarEstadoDaAPI()
            }
        )
    }

    private fun atualizarEstado(dados: JSONObject) {
        // fan_on = comando da app | fan_actual_on = estado real do Arduino
        comandoVentoinhaLigada = dados.optBoolean("fan_on", true)
        ventoinhaLigadaReal = dados.optBoolean("fan_actual_on", false)
        standbyAtivo = dados.optBoolean("standby", false)

        tvVentoinha.text = when {
            standbyAtivo -> "Ventoinha: desligada (standby)"

            // A app mandou desligar mas o Mokxi ainda não aplicou.
            !comandoVentoinhaLigada && ventoinhaLigadaReal ->
                "Ventoinha: a desligar..."

            !comandoVentoinhaLigada -> "Ventoinha: desligada pela app"

            ventoinhaLigadaReal -> "Ventoinha: ligada"

            // Comando ligado, mas está fresco (abaixo do limite).
            else -> "Ventoinha: desligada (temperatura baixa)"
        }

        tvModo.text = if (standbyAtivo) {
            "Modo: standby"
        } else {
            "Modo: automático"
        }

        // Em standby os LEDs estão sempre a piscar, por isso
        // não faz sentido mostrar ligado/desligado.
        if (standbyAtivo) {
            tvLedVerde.text = "LED verde: a piscar"
            tvLedVermelho.text = "LED vermelho: a piscar"
        } else {
            tvLedVerde.text = if (dados.optBoolean("led_1", false)) {
                "LED verde: ligado"
            } else {
                "LED verde: desligado"
            }

            tvLedVermelho.text = if (dados.optBoolean("led_2", false)) {
                "LED vermelho: ligado"
            } else {
                "LED vermelho: desligado"
            }
        }

        atualizarInterface()
    }

    private fun atualizarInterface() {
        // Os dois botões estão sempre clicáveis.
        buttonFan.isEnabled = true
        buttonStandby.isEnabled = true

        buttonFan.text = if (comandoVentoinhaLigada) {
            "Desligar a ventoinha"
        } else {
            "Ligar a ventoinha"
        }

        buttonStandby.text = if (standbyAtivo) {
            "Sair do standby"
        } else {
            "Mudar para standby"
        }
    }

    private fun atualizarEstadoDaAPI() {
        api.getActuatorState(
            token = token,
            onSuccess = { estado ->
                // Não mexer no ecrã enquanto um comando está a ser enviado.
                if (!pedidoEmCurso) {
                    atualizarEstado(estado)
                }
            },
            onError = { erro ->
                Log.e(
                    "SmartClimate",
                    "Erro ao consultar estado: $erro"
                )
            }
        )
    }

    private fun atualizarTemperatura() {
        api.getReadings(
            token = token,
            onSuccess = { leituras ->
                if (leituras.isNotEmpty()) {
                    tvTemperatura.text = "${leituras[0].value} °C"
                } else {
                    tvTemperatura.text = "-- °C"
                }
            },
            onError = { erro ->
                Log.e(
                    "SmartClimate",
                    "Erro ao consultar temperatura: $erro"
                )
            }
        )
    }

    private val updateRunnable = object : Runnable {
        override fun run() {
            atualizarTemperatura()
            atualizarEstadoDaAPI()

            handler.postDelayed(this, updateInterval)
        }
    }

    override fun onResume() {
        super.onResume()

        handler.removeCallbacks(updateRunnable)
        handler.post(updateRunnable)
    }

    override fun onPause() {
        super.onPause()
        handler.removeCallbacks(updateRunnable)
    }
}
