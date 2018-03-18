(function($) {
    $.fn.quickConfirm = function() {
        this.click(function(event) {
            event.preventDefault();
            $.ajax(this.href, {
                dataType: 'json',
                method: 'POST',
                success: function(data) {
                    modal = $(this.self).data('confirmationModal')
                    if (!modal) {
                        modal = '#confirmationModal'
                    }
                    var popup = new Foundation.Reveal($(modal));
                    popup.open();
                }.bind({
                    self: this
                }),
                error: function() {
                    var popup = new Foundation.Reveal($('#errorModal'));
                    popup.open();
                }
            });
            return this;
        });
      return this;
    }
}(jQuery));
