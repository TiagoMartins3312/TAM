package com.example.myapplication2102026

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

@Serializable

data class Reading (
    @SerialName("sensor")
    val sensor: String,

    @SerialName("value")
    val value: String,

    @SerialName("criado_em")
    val criado_em: String
)