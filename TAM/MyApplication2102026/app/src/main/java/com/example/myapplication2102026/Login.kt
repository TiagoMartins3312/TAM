package com.example.myapplication2102026

import android.R
import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

@Serializable
data class Login(
    @SerialName("username")
    val username: String,

    @SerialName("password")
    val password: String
    // Se o JSON não trouxer este campo, ele assume o valor padrão perfeitamente
)