var competition = {
  boards: {},
  round: undefined,

  initialize: function() {
    setInterval(function() {
      competition.update();
    }, 1000);
  },

  create_board: function(target, id, header) {
    var html = (
      '<div class="container">' +
      '  <div class="header">' + header + '</div>' +
      '  <object id="' + id + '" data="Board.swf" type="application/x-shockwave-flash" width="175" height="260">' +
      '    <param name="movie" value="Board.swf" />' +
      '    <param name="flashVars" value="squareWidth=10" />' +
      '  </object>' +
      '</div>'
    );
    $('#' + target).append(html);
    return board.initialize(id);
  },

  update: function() {
    this.post('/competition_state',
      {
        team_name: $.cookie('team_name'),
        password: $.cookie('password'),
      },
      function(data) {
        if (this.round === undefined) {
          this.round = data.round;
          $('#round-text').html('Dropblox - Round ' + data.round);
        } else if (this.round != data.round) {
          return;
        }

        if (data.waiting_for_players) {
          plural = (data.waiting_for_players == 1 ? ' player...' : ' players...');
          $('#login-bar').html('Waiting for ' + data.waiting_for_players + plural);
        } else if (data.started) {
          $('#login-bar').html('Competition started!');
        } else {
          $('#login-bar').html('Ready to start!');
        }

        for (var team in data.boards) {
          if (!this.boards.hasOwnProperty(team)) {
            $('#boards').append('<div id="' + team + '-container"></div>');
            this.boards[team] = this.create_board(team + '-container', team, team);
            this.boards[team].setBoardState(data.boards[team]);
          }
          this.boards[team].setBoardState(data.boards[team]);
        }
        for (var team in this.boards) {
          if (!data.boards.hasOwnProperty(team)) {
            $('#' + team + '-container').remove();
          }
        }
      }
    );
  },

  post: function(url, data, success, error) {
    $.ajax({
      type: 'POST',
      url: url,
      data: JSON.stringify(data),
      contentType: "application/json",
      dataType: "json",
      success: success,
      error: error,
    });
  },
};
