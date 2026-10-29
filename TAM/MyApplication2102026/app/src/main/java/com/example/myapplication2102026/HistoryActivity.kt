
package com.example.myapplication2102026

import android.os.Bundle
import android.util.Log
import android.widget.Button
import android.widget.TextView
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import androidx.recyclerview.widget.LinearLayoutManager
import androidx.recyclerview.widget.RecyclerView

class HistoryActivity : AppCompatActivity() {

    private lateinit var api: ApiManager
    private lateinit var token: String
    private lateinit var adapter: ReadingAdapter

    private lateinit var rvHistory: RecyclerView
    private lateinit var tvHistoryInfo: TextView
    private lateinit var buttonRefresh: Button
    private lateinit var buttonBack: Button

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_history)

        token = intent.getStringExtra("Token") ?: ""
        api = ApiManager.getInstance(this)

        rvHistory = findViewById(R.id.recyclerViewHistory)
        tvHistoryInfo = findViewById(R.id.tvHistoryInfo)
        buttonRefresh = findViewById(R.id.buttonRefreshHistory)
        buttonBack = findViewById(R.id.buttonBackHistory)

        adapter = ReadingAdapter(emptyList())
        rvHistory.layoutManager = LinearLayoutManager(this)
        rvHistory.adapter = adapter

        buttonBack.setOnClickListener {
            finish()
        }

        buttonRefresh.setOnClickListener {
            carregarHistorico()
        }

        if (token.isEmpty()) {
            Toast.makeText(
                this,
                "A sessão terminou. Inicia sessão novamente.",
                Toast.LENGTH_LONG
            ).show()

            finish()
            return
        }

        carregarHistorico()
    }

    private fun carregarHistorico() {
        buttonRefresh.isEnabled = false
        tvHistoryInfo.text = "A carregar as leituras..."

        api.getReadings(
            token = token,
            onSuccess = { leituras ->
                adapter.updateData(leituras)

                if (leituras.isEmpty()) {
                    tvHistoryInfo.text =
                        "Ainda não existem temperaturas registadas."
                } else {
                    tvHistoryInfo.text =
                        "Foram encontradas ${leituras.size} leituras."
                    rvHistory.scrollToPosition(0)
                }

                buttonRefresh.isEnabled = true
            },
            onError = { erro ->
                Log.e("SmartClimate", "Erro no histórico: $erro")

                tvHistoryInfo.text =
                    "Não foi possível carregar o histórico."

                Toast.makeText(
                    this,
                    "Erro ao carregar o histórico: $erro",
                    Toast.LENGTH_LONG
                ).show()

                buttonRefresh.isEnabled = true
            }
        )
    }
}
