package com.example.demo;

import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.URL;

/** Small HTTP helper. */
public class Net {
    public static int post(String address, String body) {
        try {
            HttpURLConnection conn = (HttpURLConnection) new URL(address).openConnection();
            conn.setRequestMethod("POST");
            conn.setDoOutput(true);
            OutputStream out = conn.getOutputStream();
            out.write(body.getBytes("UTF-8"));
            out.close();
            return conn.getResponseCode();
        } catch (Exception e) {
            return -1;
        }
    }
}
