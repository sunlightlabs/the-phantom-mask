(function(){
    $(document).ready(function(){

        var $get_started =  $('#get-started');
        $get_started.click(function() {
            var clicks = $(this).data('clicks');
            if (clicks) {
                alert('odd number of clicks');
            } else {
                alert('even number of clicks');
            }
            $(this).data("clicks", !clicks);
        });


        var $lookup_form = $("#lookup-form");
        $lookup_form.submit(function(event) {
            event.preventDefault();
            $.ajax({
                type: 'POST',
                url: URL_PREFIX + '/',
                data: $(this).serialize() + '&leg_lookup=leg_lookup',
                dataType: 'json',
                timeout: 3000,
                success: function (result) {
                    $('#legislator-display').html($(result['leg_lookup']));
                },
                error: function (jqXHR, textStatus, errorThrown) {

                },
                complete: function (jqXHR, textStatus) {

                }
            });
        })
    });
})();