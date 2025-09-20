import { initializeApp } from "https://www.gstatic.com/firebasejs/10.12.2/firebase-app.js";

const firebaseConfig = {
    apiKey: "AIzaSyAK0KvSMFZtcJXyqbfma212MUoALlYB3fo",
    authDomain: "echo-867d9.firebaseapp.com",
    projectId: "echo-867d9",
    storageBucket: "echo-867d9.appspot.com",
    messagingSenderId: "802942934876",
    appId: "1:802942934876:web:28131332211244092003d8",
    measurementId: "G-M69Q4J8P9N"
};

// Initialize Firebase
export const app = initializeApp(firebaseConfig);