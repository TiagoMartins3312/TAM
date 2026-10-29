
package com.example.myapplication2102026

import android.content.Context
import android.util.Log
import com.android.volley.DefaultRetryPolicy
import com.android.volley.Request
import com.android.volley.RequestQueue
import com.android.volley.toolbox.JsonArrayRequest
import com.android.volley.toolbox.JsonObjectRequest
import com.android.volley.toolbox.StringRequest
import com.android.volley.toolbox.Volley
import kotlinx.serialization.json.Json
import org.json.JSONObject

class ApiManager private constructor(context: Context) {

    private val requestQueue: RequestQueue =
        Volley.newRequestQueue(context.applicationContext)

    private val baseUrl = "http://10.0.2.2:5000"

    companion object {
        @Volatile
        private var INSTANCE: ApiManager? = null

        fun getInstance(context: Context): ApiManager =
            INSTANCE ?: synchronized(this) {
                INSTANCE ?: ApiManager(context).also {
                    INSTANCE = it
                }
            }
    }

    // Consultar as leituras de temperatura.
    fun getReadings(
        token: String,
        onSuccess: (List<Reading>) -> Unit,
        onError: (String) -> Unit
    ) {
        val url = "$baseUrl/data"

        val request = object : JsonArrayRequest(
            Request.Method.GET,
            url,
            null,
            { jsonArray ->
                try {
                    val listaReadings =
                        Json.decodeFromString<List<Reading>>(
                            jsonArray.toString()
                        )

                    onSuccess(listaReadings)
                } catch (e: Exception) {
                    onError(
                        "Erro ao processar as leituras: ${e.message}"
                    )
                }
            },
            { error ->
                Log.e(
                    "SmartClimate",
                    "Erro ao consultar leituras",
                    error
                )

                val statusCode = error.networkResponse?.statusCode

                if (statusCode == 401) {
                    onError("Sessão expirada ou não autorizada.")
                } else {
                    onError(
                        error.message ?: "Erro ao consultar as leituras."
                    )
                }
            }
        ) {
            override fun getHeaders(): MutableMap<String, String> {
                val headers = HashMap<String, String>()
                headers["Authorization"] = "Bearer $token"
                headers["Content-Type"] = "application/json"
                return headers
            }
        }

        request.retryPolicy = DefaultRetryPolicy(
            15000,
            0,
            DefaultRetryPolicy.DEFAULT_BACKOFF_MULT
        )

        requestQueue.add(request)
    }

    // Fazer login e devolver a resposta da API.
    fun Login(
        userRequest: Login,
        onSuccess: (String) -> Unit,
        onError: (String) -> Unit
    ) {
        val url = "$baseUrl/login"

        Log.d("SmartClimate", "URL de login: $url")

        val body = JSONObject().apply {
            put("username", userRequest.username)
            put("password", userRequest.password)
        }

        val request = JsonObjectRequest(
            Request.Method.POST,
            url,
            body,
            { resposta ->
                Log.d(
                    "SmartClimate",
                    "Resposta de login recebida"
                )

                onSuccess(resposta.toString())
            },
            { error ->
                Log.e(
                    "SmartClimate",
                    "Erro no pedido de login",
                    error
                )

                val statusCode = error.networkResponse?.statusCode

                val resposta = error.networkResponse?.data?.let {
                    String(it, Charsets.UTF_8)
                }

                if (statusCode != null) {
                    onError(
                        "Erro HTTP $statusCode: " +
                                (resposta ?: "Sem detalhes")
                    )
                } else {
                    onError(
                        error.message
                            ?: "Falha de ligação: " +
                            error.javaClass.simpleName
                    )
                }
            }
        )

        request.retryPolicy = DefaultRetryPolicy(
            15000,
            0,
            DefaultRetryPolicy.DEFAULT_BACKOFF_MULT
        )

        requestQueue.add(request)
    }

    // Consultar o estado atual da ventoinha, LEDs e modo.
    fun getActuatorState(
        token: String,
        onSuccess: (JSONObject) -> Unit,
        onError: (String) -> Unit
    ) {
        val url = "$baseUrl/actuators"

        val request = object : JsonObjectRequest(
            Request.Method.GET,
            url,
            null,
            { resposta ->
                onSuccess(resposta)
            },
            { error ->
                Log.e(
                    "SmartClimate",
                    "Erro ao consultar o estado do sistema",
                    error
                )

                onError(
                    error.message
                        ?: "Erro ao consultar o estado do sistema."
                )
            }
        ) {
            override fun getHeaders(): MutableMap<String, String> {
                val headers = HashMap<String, String>()
                headers["Authorization"] = "Bearer $token"
                headers["Content-Type"] = "application/json"
                return headers
            }
        }

        request.retryPolicy = DefaultRetryPolicy(
            15000,
            0,
            DefaultRetryPolicy.DEFAULT_BACKOFF_MULT
        )

        requestQueue.add(request)
    }

    // Alterar o estado da ventoinha, dos LEDs ou do modo.
    fun setActuatorState(
        token: String,
        dados: JSONObject,
        onSuccess: (JSONObject) -> Unit,
        onError: (String) -> Unit
    ) {
        val url = "$baseUrl/actuators"

        val request = object : JsonObjectRequest(
            Request.Method.POST,
            url,
            dados,
            { resposta ->
                Log.d(
                    "SmartClimate",
                    "Estado do sistema atualizado"
                )

                onSuccess(resposta)
            },
            { error ->
                Log.e(
                    "SmartClimate",
                    "Erro ao alterar o estado do sistema",
                    error
                )

                val resposta = error.networkResponse?.data?.let {
                    String(it, Charsets.UTF_8)
                }

                val statusCode = error.networkResponse?.statusCode

                if (statusCode != null) {
                    onError(
                        "Erro HTTP $statusCode: " +
                                (resposta ?: "Sem detalhes")
                    )
                } else {
                    onError(
                        error.message
                            ?: "Erro ao alterar o estado do sistema."
                    )
                }
            }
        ) {
            override fun getHeaders(): MutableMap<String, String> {
                val headers = HashMap<String, String>()
                headers["Authorization"] = "Bearer $token"
                headers["Content-Type"] = "application/json"
                return headers
            }
        }

        request.retryPolicy = DefaultRetryPolicy(
            15000,
            0,
            DefaultRetryPolicy.DEFAULT_BACKOFF_MULT
        )

        requestQueue.add(request)
    }

    // Teste temporário da ligação à API.
    fun testConnection(
        onSuccess: (String) -> Unit,
        onError: (String) -> Unit
    ) {
        val url = "$baseUrl/"

        val request = StringRequest(
            Request.Method.GET,
            url,
            { resposta ->
                Log.d(
                    "SmartClimate",
                    "Teste GET recebido: $resposta"
                )

                onSuccess(resposta)
            },
            { error ->
                Log.e(
                    "SmartClimate",
                    "Erro no teste GET",
                    error
                )

                onError(
                    error.message ?: error.javaClass.simpleName
                )
            }
        )

        request.retryPolicy = DefaultRetryPolicy(
            15000,
            0,
            DefaultRetryPolicy.DEFAULT_BACKOFF_MULT
        )

        requestQueue.add(request)
    }
}
