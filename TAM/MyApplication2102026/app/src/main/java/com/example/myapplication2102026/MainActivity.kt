package com.example.myapplication2102026

import android.content.Intent
import android.os.Bundle
//import android.os.Bundle
import android.widget.Button
import android.widget.TextView
import android.widget.Toast
import androidx.activity.enableEdgeToEdge
import androidx.appcompat.app.AppCompatActivity
import com.android.volley.Request
import com.android.volley.toolbox.JsonObjectRequest
import com.android.volley.toolbox.Volley
import kotlinx.serialization.encodeToString
import kotlinx.serialization.json.Json
import org.json.JSONObject
import android.util.Log


class MainActivity : AppCompatActivity() {

    private lateinit var botao: Button
    private lateinit var txtusername: TextView
    private lateinit var txtPassword: TextView
    private lateinit var api: ApiManager

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        setContentView(R.layout.activity_main)
        api = ApiManager.getInstance(this)
        setupView()
    }

    private fun setupView(){
        botao = findViewById<Button>(R.id.button4)
        txtusername = findViewById<TextView>(R.id.editTextText3)
        txtPassword = findViewById<TextView>(R.id.editTextTextPassword2)
        //botao.text = getString(R.string.btNextText);
        botao.setOnClickListener {
            Log.d("SmartClimate", "Botão LOGIN clicado")

            botao.isEnabled = false
            callApiLogin()
        }
    }

    private fun callApiLogin(){
        api.Login(
            userRequest = Login(
                username = txtusername.text.toString(),
                password = txtPassword.text.toString()
            ),
            onSuccess = { json ->
                val userObj = Json.decodeFromString<LoginResponse>(json)
                SecureStorageManager(this).savePassword(txtPassword.text.toString())
                SecureStorageManager(this).saveUsername(txtusername.text.toString())
                SecureStorageManager(this).saveToken(userObj.token)
                goTo(userObj.token)
                botao.isEnabled = true
            },
            onError = { erro ->
                Toast.makeText(this, "Erro: $erro", Toast.LENGTH_LONG).show()
                botao.isEnabled = true
            })
    }

    private fun goTo(token:String){
        val intent = Intent(this, MainActivity2::class.java)
        intent.putExtra("Token",token)
        startActivity(intent)
    }

    fun callLoginAPI(){

        // 1. Inicializar a fila de requisições do Volley
        val queue = Volley.newRequestQueue(this)
        val url = "https://flask-tam-kotlin.vercel.app/login" // String XML
        val login = Login(txtusername.text.toString(), txtPassword.text.toString())
        val jsonString = Json.encodeToString(login)
        val jsonBody = JSONObject(jsonString)

        // 4. Monte a requisição padrão do Volley
        val jsonObjectRequest = JsonObjectRequest(
            Request.Method.POST, url, jsonBody,
            { response ->
                val userObj = Json.decodeFromString<LoginResponse>(response.toString())
                println(userObj) // User(name=John Doe, age=30,

                // Inicializar a classe passando o contexto
                val secureStorage = SecureStorageManager(this)
                secureStorage.savePassword(txtPassword.text.toString())
            },
            { error ->
                println("Erro: ${error.message}")
            }
        )
        // 3. Adicionar a requisição à fila
        queue.add(jsonObjectRequest)
    }
}

