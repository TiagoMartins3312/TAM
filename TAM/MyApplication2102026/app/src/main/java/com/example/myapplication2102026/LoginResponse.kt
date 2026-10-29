package com.example.myapplication2102026

import android.R
import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

@Serializable
data class LoginResponse (

    @SerialName("id")
    val id: Int,

    @SerialName("token")
    val token: String,

    @SerialName("username")
    val username: String
    )

