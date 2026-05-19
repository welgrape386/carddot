import axios from "axios";

export const api = axios.create({
  baseURL: "https://carddot-s4vn.onrender.com",
  headers: {
    "Content-Type": "application/json",
  },
});