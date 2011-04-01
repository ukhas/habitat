function list_telem() {
    $db = $.couch.db("habitat");
    $db.view("habitat/payload_telem",
        {"limit": "20", "descending": "true", success: function(data) {
            $("#telems").html(data);
        }});
};

