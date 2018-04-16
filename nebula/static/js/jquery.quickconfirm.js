(function($) {
    $.fn.quickConfirm = function(options) {
        // This is the easiest way to have default options.
        const settings = $.extend({
            success: function(data) {
                modal = $(this.self).data('confirmationModal')
                if (!modal) {
                    modal = '#confirmationModal'
                }
                const jqmodal = $(modal)
                const popup = new Foundation.Reveal(jqmodal);
                popup.open();
                setTimeout(function () {
                  const popup = new Foundation.Reveal(jqmodal);
                  popup.close()
                  $('.reveal-overlay').remove()
                }, 2500)
            },
            error: function () {
              var popup = new Foundation.Reveal($('#errorModal'));
              popup.open();
            }
        }, options );

        this.off()
        this.click(function(event) {
            event.preventDefault();
            $.ajax(this.href, {
                dataType: 'json',
                method: 'POST',
                success: settings.success.bind({
                    self: this
                }),
                error: settings.error.bind({
                    self: this
                })
            });
            return this;
        });
      return this;
    }
}(jQuery));
