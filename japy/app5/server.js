const express = require("express");
const data = require("./data.json")

const app = express();

app.get("/", (req, res) => {
    res.send("Hello, Welcome to the Node App")
})

app.get("/data", (req, res) => {
    res.json(data)
})

app.get("/app5", (req, res) => {
    res.json(data)
})

app.listen(80, () => {
    console.log("App is running")
});