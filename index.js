const express = require("express");
const app = express();
const cors = require("cors")
const fileUpload = require("express-fileupload")
const PORT = process.env.PORT || 4000;
const { PythonShell } = require('python-shell')

app.use(express.static(__dirname + '/public'));
app.use(cors());
app.use(fileUpload({
    useTempFiles: true,
    tempFileDir: '/tmp/'
}))

app.use(function (req, res, next) {
    res.header("Access-Control-Allow-Origin", '*');
    res.header("Access-Control-Allow-Credentials", true);
    res.header('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS');
    res.header("Access-Control-Allow-Headers", 'Origin,X-Requested-With,Content-Type,Accept,content-type,application/json');
    next();
});

app.get('/', function(req, res) {
    res.send("hello world");
});

app.post('/api/submitdata', function (req, res) {
    let options = {
        mode: 'text',
        pythonOptions: ['-u'],
        scriptPath: __dirname,
        args: [req.files.districtData.tempFilePath, req.files.labData.tempFilePath]
    };
    PythonShell.run('script.py', options, function (err, result) {
        if (err) throw err;
        res.sendFile(__dirname + '/output.json')
    }); 
    res.send('hello')
})

app.listen(PORT, function () {
    console.log(`Server started on ${PORT}`);
})
