package com.example.myapplication2102026

import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.TextView
import androidx.recyclerview.widget.RecyclerView

class ReadingAdapter(private var readings: List<Reading>) :
    RecyclerView.Adapter<ReadingAdapter.ReadingViewHolder>() {

    // Guarda as referências visuais de cada item
    class ReadingViewHolder(view: View) : RecyclerView.ViewHolder(view) {
        val tvId: TextView = view.findViewById(R.id.tvId)
        val tvValue: TextView = view.findViewById(R.id.tvValue)
        val tvTimestamp: TextView = view.findViewById(R.id.tvTimestamp)
    }

    // "Insufla" (dá vida) ao XML do item
    override fun onCreateViewHolder(parent: ViewGroup, viewType: Int): ReadingViewHolder {
        val view = LayoutInflater.from(parent.context)
            .inflate(R.layout.item_reading, parent, false)
        return ReadingViewHolder(view)
    }

    // Preenche os dados em cada linha
    override fun onBindViewHolder(holder: ReadingViewHolder, position: Int) {
        val reading = readings[position]

        holder.tvId.text = "Sensor: ${reading.sensor}"
        holder.tvValue.text = "Temperatura: ${reading.value} °C"
        holder.tvTimestamp.text = "Registada em: ${reading.criado_em}"
    }

    fun updateData(newReadings: List<Reading>) {
        this.readings = newReadings
        notifyDataSetChanged() //
    }

    // Diz à lista quantos itens existem no total
    override fun getItemCount(): Int = readings.size
}