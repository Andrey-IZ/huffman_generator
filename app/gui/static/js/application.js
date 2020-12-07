
$(document).ready(function(){
    //connect to the socket server.
    var socket = io.connect('http://' + document.domain + ':' + location.port + '/stats');
    var msg_received = [];

    //receive details from server
    socket.on('update_stats', function(msg) {
        if (jQuery.isEmptyObject(msg))
            return
        strMsg = "{ done:" + msg.done + ", delayed:" + msg.delayed + ", exception:" + msg.exception + "}"
        console.log("stats: " + strMsg);

        if (msg_received.length >= 1){
            msg_received.shift()
        }            
        msg_received.push(strMsg);
        msg_string = 'Статистика процесса: ';
        for (var i = 0; i < msg_received.length; i++){
            msg_string = msg_string + '<p>' + msg_received[i] + '</p>';
        }
        $('#log').html(msg_string);
    });

});
