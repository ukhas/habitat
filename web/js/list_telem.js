function list_telem() {
    $db = $.couch.db("habitat");
    $db.view("habitat/payload_telem",
        {"limit": "20", "descending": "true", success: function(data) {
            for(var i = 0; i < data.rows.length; i++) {
                $("#telems").append(data.rows[i].id);
                $("#telems").append("<br />");
        }});
};

