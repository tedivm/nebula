
$( document ).ready(function() {

  /*
   * Label Management
   */
  $('.serverlabel').on('keydown', function(e) {
    // Did they hit escape?
    if(e.keyCode == 27) {
      $(this).text($(this).data('originallabel'))
      window.getSelection().removeAllRanges()
    }

    // Did they hit enter?
    if(e.keyCode == 13)
    {
      e.preventDefault()
      const id = $(this).attr('id')
      const firstLabel = $(this).data('originallabel')
      const newLabel = $(this).text().replace(/ |\n/g,'')
      if (firstLabel != newLabel && newLabel.length > 0) {
        console.log(`input field changed on ${id}`)
        $.ajax($(this).attr('href'), {
            dataType: 'json',
            method: 'POST',
            data: {'label': newLabel},
            success: function(data) {
              $(this).text(newLabel)
              $(this).data('originallabel', newLabel)
              window.getSelection().removeAllRanges()
            }.bind({
                self: this
            }),
            error: function() {
                var popup = new Foundation.Reveal($('#errorModal'))
                popup.open()
            }
        })
      }
    }
  })

  /*
   * Automatic Shutdown
   */
   $('input.shutdowntime').fdatepicker({
     format: 'mm-dd-yyyy hh:ii',
     disableDblClickSelection: true,
     pickTime: true,
     onRender: filterPast
   }).change(function () {
     const value = $(this).val()
     let newTimestamp = ''
     if (value.length > 0) {
        newTimestamp = Date.parse($(this).val()) / 1000
     }
     $('#shutdowntimestamp').val(newTimestamp)
   })

  $('i.scheduleshutdown').each(function () {
    const icon = $(this)
    const shutdowntimestamp = icon.data('shutdowntime')
    if (Number.isInteger(shutdowntimestamp)) {
      const shutdowntime = timestampToString(shutdowntimestamp)
      icon.prop('title', `Shutdown Scheduled for ${shutdowntime}`);
    }
  })

  $('i.scheduleshutdown').click(function () {
    const icon = $(this)
    const instanceid = icon.data('instanceid')
    const shutdowntimestamp = icon.data('shutdowntime')
    console.log(`Currently scheduled to shutdown ${instanceid} at ${shutdowntimestamp}`)
    let shutdowntime = ''
    if (Number.isInteger(shutdowntimestamp)) {
      shutdowntime = timestampToString(shutdowntimestamp)
    }

    var popup = new Foundation.Reveal($('#scheduleShutdownModal')).open()
    $('#shutdownTimeSelector').val(shutdowntime)
    $('#shutdownTimeSelector').data('instanceid', instanceid)
    $('#shutdownTimeSelector').fdatepicker({
      format: 'mm-dd-yyyy hh:ii',
      disableDblClickSelection: true,
      pickTime: true,
      onRender: filterPast
    });
  })

  $('#shutdownTimeSubmit').click(function () {
    const instanceid = $('#shutdownTimeSelector').data('instanceid')
    const shutdowntime = $('#shutdownTimeSelector').val()
    const timestamp = Date.parse(shutdowntime) / 1000
    const url = `/server/${instanceid}/schedulestop`
    console.log(`Scheduling shutdown of instance ${instanceid} for ${shutdowntime} (${timestamp})`)
    $.ajax(url, {
        dataType: 'json',
        method: 'POST',
        data: {
          'stoptime': timestamp
        },
        success: function(data) {
          const icon = $(`#scheduleShutdownButton_${instanceid}`)
          icon.data('shutdowntime', timestamp).addClass('alert')
          const shutdowntime = timestampToString(timestamp)
          icon.prop('title', `Shutdown Scheduled for ${shutdowntime}`);
        }.bind({
            self: this
        }),
        error: function() {
            new Foundation.Reveal($('#errorModal')).open()
        }
    })
  })


  $(document).foundation()
})


function timestampToString (timestamp) {
  var date = new Date(timestamp*1000);
  var day = date.getDate()
  var month = date.getMonth() + 1
  var year = date.getFullYear()
  var hours = date.getHours()
  var minutes = date.getMinutes()
  return `${month}-${day}-${year} ${hours}:${minutes}`
}

function filterPast (date) {
  var dateOffset = (24*60*60*1000); //5 days
  var now = new Date();
  now.setTime(now.getTime() - dateOffset);
  if (date.getFullYear() < now.getFullYear()) {
    return 'disabled'
  } else if (date.getFullYear() == now.getFullYear()) {
    if (date.getMonth() < now.getMonth()) {
      return 'disabled'
    } else if (date.getMonth() == now.getMonth()) {
      if (date.getDate() < now.getDate()) {
        return 'disabled'
      }
    }
  }
  return ''
}
