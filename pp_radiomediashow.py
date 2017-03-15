from pp_gapshow import GapShow
from pp_medialist import MediaList

class RadioMediaShow(GapShow):

    def __init__(self,
                 show_id,
                 show_params,
                 root,
                 canvas,
                 showlist,
                 pp_dir,
                 pp_home,
                 pp_profile,
                 command_callback):


        # init the common bits
        GapShow.__init__(self,
                         show_id,
                         show_params,
                         root,
                         canvas,
                         showlist,
                         pp_dir,
                         pp_home,
                         pp_profile,
                         command_callback)


    def play(self,end_callback,show_ready_callback, direction_command,level,controls_list):

        # use the appropriate medialist
        self.medialist=MediaList(self.show_params['sequence'])

        GapShow.play(self,end_callback,show_ready_callback, direction_command,level,controls_list)

    def handle_input_event_this_show(self,symbol):
        # for radiobuttonshow the symbolic names are links to play tracks, also a limited number of in-track operations
        # find the first entry in links that matches the symbol and execute its operation
        # print 'radiobuttonshow ',symbol
        found,link_op,link_arg=self.path.find_link(symbol,self.links)
        # print 'input event',symbol,link_op
        if found is True:
            if link_op == 'play':
                self.do_play(link_arg)

            elif link_op == 'exit':
                #exit the show
                self.exit()

            elif link_op == 'stop':
                self.stop_timers()
                if self.current_player is not None:
                    if self.current_track_ref == self.first_track_ref  and self.level != 0:
                        # if quiescent then set signal to stop the show when track has stopped
                        self.user_stop_signal=True
                    self.current_player.input_pressed('stop')

            elif link_op== 'return':
                # return to the first track
                if self.current_track_ref != self.first_track_ref:
                    self.do_play(self.first_track_ref)

            # in-track operations
            elif link_op =='pause':
                if self.current_player is not  None:
                    self.current_player.input_pressed(link_op)

            elif link_op in ('no-command','null'):
                return

            elif link_op[0:4] == 'omx-' or link_op[0:6] == 'mplay-'or link_op[0:5] == 'uzbl-':
                if self.current_player is not None:
                    self.current_player.input_pressed(link_op)

            else:
                self.mon.err(self,"unknown link command: "+ link_op)
                self.end('error',"unknown link command: "+ link_op)

    def do_play(self,track_ref):
        # if track_ref != self.current_track_ref:
        # cancel the show timeout when playing another track
        if self.show_timeout_timer is not None:
            self.canvas.after_cancel(self.show_timeout_timer)
            self.show_timeout_timer=None
        # print '\n NEED NEXT TRACK'
        self.next_track_signal=True
        self.next_track_op='play'
        self.next_track_arg=track_ref
        if self.shower is not None:
            # print 'current_shower not none so stopping',self.mon.id(self.current_shower)
            self.shower.do_operation('stop')
        elif self.current_player is not None:
            # print 'current_player not none so stopping',self.mon.id(self.current_player), ' for' ,track_ref
            self.current_player.input_pressed('stop')
        else:
            return
