package com.example.myapplication2102026

import android.content.Context
import android.content.SharedPreferences
import androidx.security.crypto.EncryptedSharedPreferences
import androidx.security.crypto.MasterKey

class SecureStorageManager(context: Context) {

    // 1. Criar ou recuperar a Chave Mestra (guardada no hardware seguro do telemóvel)
    private val masterKey = MasterKey.Builder(context)
        .setKeyScheme(MasterKey.KeyScheme.AES256_GCM)
        .build()

    // 2. Inicializar o EncryptedSharedPreferences
    private val sharedPreferences: SharedPreferences = EncryptedSharedPreferences.create(
        context,
        "ficheiro_seguro_prefs", // Nome do ficheiro XML gerado internamente
        masterKey,
        EncryptedSharedPreferences.PrefKeyEncryptionScheme.AES256_SIV, // Encripta as chaves
        EncryptedSharedPreferences.PrefValueEncryptionScheme.AES256_GCM // Encripta os valores
    )

    // Função para guardar a password
    fun saveUsername(username: String) {
        sharedPreferences.edit()
            .putString("USERNAME", username)
            .apply() // .apply() é assíncrono, .commit() é síncrono
    }

    // Função para ler a password
    fun getUsername(): String? {
        return sharedPreferences.getString("USERNAME", null)
    }

    // Função para guardar a password
    fun savePassword(password: String) {
        sharedPreferences.edit()
            .putString("USER_PASSWORD", password)
            .apply() // .apply() é assíncrono, .commit() é síncrono
    }

    // Função para ler a password
    fun getPassword(): String? {
        return sharedPreferences.getString("USER_PASSWORD", null)
    }

    fun saveToken(token: String) {
        sharedPreferences.edit()
            .putString("TOKEN", token)
            .apply() // .apply() é assíncrono, .commit() é síncrono
    }

    // Função para ler a password
    fun getToken(): String? {
        return sharedPreferences.getString("TOKEN", null)
    }

    // Função para apagar tudo (ex: no logout)
    fun clearCredentials() {
        sharedPreferences.edit().clear().apply()
    }
}