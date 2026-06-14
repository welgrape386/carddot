import axios from "axios";

export const api = axios.create({
  baseURL: "https://carddot-s4vn.onrender.com",
  headers: {
    "Content-Type": "application/json",
  },
});

api.interceptors.request.use((config) => {
  const token = sessionStorage.getItem("token");

  if (token) {
    config.headers.Authorization = token;
  }

  return config;
});