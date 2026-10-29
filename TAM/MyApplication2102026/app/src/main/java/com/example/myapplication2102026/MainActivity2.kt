
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
import android.widget.LinearLayout
import android.widget.SeekBar
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
    private lateinit var tvFanSpeed: TextView

    private lateinit var speedControls: LinearLayout
    private lateinit var seekBarFanSpeed: SeekBar

    private lateinit var buttonFan: Button
    private lateinit var buttonMode: Button
    private lateinit var buttonLogs: Button
    private lateinit var buttonSair: Button

    private var ventoinhaLigada = false
    private var modoAtual = "automatico"
    private var velocidadeAtual = 50

    private val handler = Handler(Looper.getMainLooper())
    private val updateInterval = 30000L

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
        tvFanSpeed = findViewById(R.id.tvFanSpeed)

        speedControls = findViewById(R.id.speedControls)
        seekBarFanSpeed = findViewById(R.id.seekBarFanSpeed)

        buttonFan = findViewById(R.id.buttonFan)
        buttonMode = findViewById(R.id.buttonMode)
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

        // Alternar entre o modo automático e o modo manual.
        buttonMode.setOnClickListener {
            val novoModo = if (modoAtual == "automatico") {
                "manual"
            } else {
                "automatico"
            }

            enviarAlteracao(
                JSONObject().put("mode", novoModo)
            )
        }

        // Ligar ou desligar a ventoinha no modo manual.
        buttonFan.setOnClickListener {
            val novoEstado = !ventoinhaLigada

            val velocidade = if (novoEstado) {
                if (velocidadeAtual == 0) 50 else velocidadeAtual
            } else {
                velocidadeAtual
            }

            val dados = JSONObject()
                .put("fan_on", novoEstado)
                .put("fan_speed", velocidade)
                .put("mode", "manual")

            enviarAlteracao(dados)
        }

        // Alterar a velocidade através da barra deslizante.
        seekBarFanSpeed.max = 100

        seekBarFanSpeed.setOnSeekBarChangeListener(
            object : SeekBar.OnSeekBarChangeListener {

                override fun onProgressChanged(
                    seekBar: SeekBar?,
                    progress: Int,
                    fromUser: Boolean
                ) {
                    tvFanSpeed.text =
                        "Velocidade da ventoinha: $progress%"
                }

                override fun onStartTrackingTouch(seekBar: SeekBar?) {
                    // Não é necessária uma ação neste momento.
                }

                override fun onStopTrackingTouch(seekBar: SeekBar?) {
                    if (modoAtual == "manual") {
                        val velocidade = seekBarFanSpeed.progress
                        velocidadeAtual = velocidade

                        val dados = JSONObject()
                            .put("fan_speed", velocidade)
                            .put("fan_on", velocidade > 0)
                            .put("mode", "manual")

                        enviarAlteracao(dados)
                    }
                }
            }
        )

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
        buttonFan.isEnabled = false
        buttonMode.isEnabled = false
        seekBarFanSpeed.isEnabled = false

        api.setActuatorState(
            token = token,
            dados = dados,
            onSuccess = { resposta ->
                atualizarEstado(resposta)

                Toast.makeText(
                    this,
                    "Estado do sistema atualizado.",
                    Toast.LENGTH_SHORT
                ).show()

                buttonFan.isEnabled = true
                buttonMode.isEnabled = true
                seekBarFanSpeed.isEnabled = modoAtual == "manual"
            },
            onError = { erro ->
                Toast.makeText(
                    this,
                    "Não foi possível atualizar o sistema: $erro",
                    Toast.LENGTH_LONG
                ).show()

                buttonFan.isEnabled = true
                buttonMode.isEnabled = true
                seekBarFanSpeed.isEnabled = modoAtual == "manual"

                atualizarEstadoDaAPI()
            }
        )
    }

    private fun atualizarEstado(dados: JSONObject) {
        ventoinhaLigada = dados.optBoolean("fan_on", false)
        modoAtual = dados.optString("mode", "automatico")
        velocidadeAtual = dados.optInt("fan_speed", 50)

        tvVentoinha.text = if (ventoinhaLigada) {
            "Ventoinha: ligada"
        } else {
            "Ventoinha: desligada"
        }

        val nomeModo = when (modoAtual) {
            "automatico" -> "automático"
            "manual" -> "manual"
            "noturno" -> "noturno"
            else -> modoAtual
        }

        tvModo.text = "Modo: $nomeModo"

        tvLedVerde.text = if (dados.optBoolean("led_1", true)) {
            "LED verde: ligado"
        } else {
            "LED verde: desligado"
        }

        tvLedVermelho.text = if (dados.optBoolean("led_2", false)) {
            "LED vermelho: ligado"
        } else {
            "LED vermelho: desligado"
        }

        seekBarFanSpeed.progress = velocidadeAtual
        tvFanSpeed.text = "Velocidade da ventoinha: $velocidadeAtual%"

        atualizarInterface()
    }

    private fun atualizarInterface() {
        speedControls.visibility = if (modoAtual == "manual") {
            View.VISIBLE
        } else {
            View.GONE
        }

        seekBarFanSpeed.isEnabled = modoAtual == "manual"

        buttonFan.text = if (ventoinhaLigada) {
            "Desligar a ventoinha"
        } else {
            "Ligar a ventoinha"
        }

        buttonMode.text = if (modoAtual == "automatico") {
            "Mudar para modo manual"
        } else {
            "Mudar para modo automático"
        }
    }

    private fun atualizarEstadoDaAPI() {
        api.getActuatorState(
            token = token,
            onSuccess = { estado ->
                atualizarEstado(estado)
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
