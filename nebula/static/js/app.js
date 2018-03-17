
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

  $('#serverlist_refresh').click(function () {
    updateServerTable()
  })

  $(document).foundation()

  new Clipboard('.copy');
  $('.datatable').DataTable({
    "paging":   false,
    "searching":   false,
    "order": [[ 0, "desc" ]]
  });

  $('a.oneclickconfirm').quickConfirm()

})

function updateServerTable () {
  const admin = $('#serverlist_refresh').hasClass('admin')
  const url = admin ? '/admin/servers/index.json' : '/servers/index.json'
  $.ajax(url, {
      dataType: 'json',
      success: function(data) {
        const instanceIds = []

        // Add or update rows in the instance table.
        for (const server of data) {
          instanceIds.push(server.instance_id)
          if($(`#row_${server.instance_id}`).length) {

            if (admin) {
              $(`#state_${server.instance_id}`).html(`<a href="/admin/state/${server.state}">${server.state}</a>`)
            } else {
              $(`#state_${server.instance_id}`).text(server.state)
            }

            $(`#status_${server.instance_id}`).text(server.status ? server.status : '')

            if (!server.status || server.status !== 'Live') {
              $(`#row_${server.instance_id}`).addClass('action-required-instance')
            } else {
              $(`#row_${server.instance_id}`).removeClass('action-required-instance')
            }

            if (server.label) {
              $(`#serverlabel_${server.instance_id}`).text(server.label)
            } else if (server.name) {
              $(`#serverlabel_${server.instance_id}`).text(server.name)
            } else {
              $(`#serverlabel_${server.instance_id}`).text('')
            }

            if (server.launch) {
              const launch = gmtToLocal(server.launch)
              $(`#launch_${server.instance_id}`).text(launch)
            } else {
                $(`#launch_${server.instance_id}`).text('')
            }
            $(`#cost_${server.instance_id}`).text(server.cost ? `$${server.cost}` : '$0.00')
            $(`#control_${server.instance_id}`).html(getControlPanel(server))
          } else {
            $('#servertable > tbody:last-child').append(getNewRow(server, admin))
            const isEven = $('#servertable > tbody > tr').length % 2 === 0
            $('#servertable > tbody:last-child').addClass(isEven ? 'even' : 'odd')
          }
        }

        // Remove instances that are no longer present.
        $('#servertable > tbody > tr').each(function () {
          const row = $(this)
          const instance_id = row.attr('id').split('_')[1]
          if (!instanceIds.includes(instance_id)) {
            row.remove()
          }
        })

        // Format alternating rows differently.
        let rownum = 0
        $('#servertable > tbody > tr').each(function () {
          const row = $(this)
          const instance_id = row.attr('id').split('_')[1]
          if (!instanceIds.includes(instance_id)) {
            row.remove()
          } else {
            rownum++
            if (rownum % 2 === 0) {
              row.addClass('even').removeClass('odd')
            } else {
              row.addClass('odd').removeClass('even')
            }
          }
        })

      },
      error: function() {
          new Foundation.Reveal($('#errorModal')).open()
      }
  })
}

function getNewRow(server, admin=false) {
  const controlPanel = getControlPanel(server)
  let output = `
  <tr id="row_${server.instance_id}" class="${!server.status || server.status !== 'Live' ? action-required-instance : ''}">
    <td id="launch_${server.instance_id}">${gmtToLocal(server.launch)}</td>
    <td id="cost_${server.instance_id}"$${server.cost}</td>
    `

  if (admin) {
    output += `
      <td id="user_${server.instance_id}"><a href="/admin/users/${server.user}">${server.user}</a></td>
      `
  }

  let label = ''
  if (server.label) {
    label = server.label
  } else if (server.name) {
    label = server.name
  }

  output += `
    <td id="group_${server.instance_id}">${server.group ? server.group.substring(0, 8) : ''}</td>
    <td contenteditable="true" class="serverlabel" id="serverlabel_${server.instance_id}" data-originallabel="" href="/server/${server.instance_id}/label">${label}</td>
    <td id="instanceid_${server.instance_id}">${server.instance_id}<i data-tooltip data-disable-hover="false" data-clipboard-text="${server.instance_id}" title="Copy '${server.instance_id}' to clipboard." class="fa-clipboard fa copy"></i></td>
    <td id="ipaddress_${server.instance_id}">${server.private_ip_address}<i data-tooltip data-disable-hover="false" data-clipboard-text="ssh -A ${server.private_ip_address}" title="Copy 'ssh ${server.private_ip_address}' to clipboard." class="fa-clipboard fa copy"></i></td>
    <td id="instancetype_${server.instance_id}">${server.instance_type}</td>
    <td id="diskspace_${server.instance_id}" data-sort="${server.disk_space}">${server.disk_space} (${server.disk_space * 0.1}/month)</td>
    `

  if (admin) {
    output += `
      <td id="image_${server.instance_id}">${server.image_id}</td>
      `
  }

  output += `
    <td id="profile_${server.instance_id}" title='${server.profile}'>${server.profile}</td>
    <td id="status_${server.instance_id}">${server.status ? server.status : ''}</td>
    `

  if (admin) {
    output += `<td id="state_${server.instance_id}"><a href="/admin/state/${server.state}">${server.state}</a></td>`
  } else {
    output += `<td id="state_${server.instance_id}">${server.state}</td>`
  }

  output += `
    <td id="control_${server.instance_id}">${controlPanel}</td>
  </tr>`

  return output
}

function getControlPanel(server) {
  const state = server.state
  let controlPanel = ``

  // Start
  if (state === 'stopped') {
    controlPanel += `
          <a href="/servers/${server.instance_id}/start" data-confirmation-modal='#confirmationModalStart' class="oneclickconfirm">
            <i data-tooltip data-disable-hover="false" title='start' class="has-tip fa-play fa"></i>
          </a>`
  } else {
    controlPanel += `<i data-tooltip title='start' class="fa-play fa disabled has-tip"></i>`
  }

  // Stop
  if (state === 'running') {
    controlPanel += `
          <a href="/servers/${server.instance_id}/stop" data-confirmation-modal='#confirmationModalStop' class="oneclickconfirm">
            <i data-tooltip data-disable-hover="false" title='stop' class="has-tip fa-stop fa"></i>
          </a>`
  } else {
    controlPanel += `<i data-tooltip title='stop' class="fa-stop fa disabled has-tip"></i>`
  }

  // Scedule Shutdown
  if (state === 'running') {
    if (server.shutdown) {
      controlPanel +=`<i data-tooltip data-disable-hover="false" id="scheduleShutdownButton_${server.instance_id}" data-instanceid="${server.instance_id}" title='schedule' class="has-tip fa-clock-o fa scheduleshutdown alert" data-shutdowntime=${server.shutdown}></i>`
    } else {
      controlPanel +=`<i data-tooltip data-disable-hover="false" id="scheduleShutdownButton_${server.instance_id}" data-instanceid="${server.instance_id}" title='schedule' class="has-tip fa-clock-o fa scheduleshutdown"></i>`
    }
  } else {
    controlPanel += `<i data-tooltip title='Schedule Shutdown' class="fa-clock-o fa disabled has-tip"></i>`
  }

  // reboot
  if (state === 'running') {
    controlPanel +=`
          <a href="/servers/${server.instance_id}/reboot" data-confirmation-modal='#confirmationModalRestart' class="oneclickconfirm">
            <i data-tooltip data-disable-hover="false" title='restart' class="has-tip fa-circle fa"></i>
          </a>`
  } else {
    controlPanel += `<i data-tooltip title='restart' class="fa-circle fa disabled has-tip"></i>`
  }

  // terminate
  if (state !== 'terminated') {
    controlPanel +=`
          <a href="/server/${server.instance_id}/terminate">
            <i data-tooltip data-disable-hover="false" title='terminate' class="has-tip fa-times fa"></i>
          </a>`
  } else {
    controlPanel += `<i data-tooltip title='terminate' class="fa-times fa disabled has-tip"></i>`
  }

  // terminate group
  if (server.group) {
    controlPanel +=`
          <a href="/server/${server.group}/terminate/group">
            <i data-tooltip data-disable-hover="false" title="terminate-group" class="has-tip fa-power-off fa"></i>
          </a>`
  } else {
    controlPanel += `<i data-tooltip title='terminate-group' class="fa-power-off fa disabled has-tip"></i>`
  }

  return controlPanel
}

function timestampToString (timestamp) {
  var date = new Date(timestamp*1000);
  var day = date.getDate()
  var month = date.getMonth() + 1
  var year = date.getFullYear()
  var hours = date.getHours()
  var minutes = date.getMinutes()
  return `${month}-${day}-${year} ${hours}:${minutes}`
}

function gmtToLocal (time) {
  const date = new Date(time)
  let month = date.getMonth() + 1
  if (month < 10) {
    month = `0${month}`
  }
  return `${date.getFullYear()}-${month}-${date.getDate()} ${date.getHours()}:${date.getMinutes()}`
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
