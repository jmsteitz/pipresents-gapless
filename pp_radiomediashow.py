from pp_show import Show
from pp_medialist import MediaList

class RadioMediaShow(Show):

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
        Show.base__init__(self,
                         show_id,
                         show_params,
                         root,
                         canvas,
                         showlist,
                         pp_dir,
                         pp_home,
                         pp_profile,
                         command_callback)


    # def play(self,end_callback,show_ready_callback, direction_command,level,controls_list):
    #
    #     # use the appropriate medialist
    #     self.medialist=MediaList(self.show_params['sequence'])
    #
    #     GapShow.play(self,end_callback,show_ready_callback, direction_command,level,controls_list)

    def play(self,end_callback,show_ready_callback, parent_kickback_signal,level,controls_list):
        # use the appropriate medialist
        self.medialist=MediaList(self.show_params['sequence'])

        self.mon.newline(3)
        self.mon.trace(self, self.show_params['show-ref'])

        Show.base_play(self,end_callback,show_ready_callback,parent_kickback_signal, level,controls_list)

        # unpack show parameters

        reason,message,self.show_timeout = Show.calculate_duration(self,self.show_params['show-timeout'])
        if reason=='error':
            self.mon.err(self,'ShowTimeout has bad time: '+self.show_params['show-timeout'])
            self.end('error','ShowTimeout has bad time: '+self.show_params['show-timeout'])

        self.track_count_limit = int(self.show_params['track-count-limit'])

        reason,message,self.interval = Show.calculate_duration (self, self.show_params['interval'])
        if reason=='error':
            self.mon.err(self,'Interval has bad time: '+self.show_params['interval'])
            self.end('error','Interval has bad time: '+self.show_params['interval'])

        # delete eggtimer started by the parent
        if self.previous_shower is not None:
            self.previous_shower.delete_eggtimer()

        self.start_show()

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

# ***************************
# Show sequencing
# ***************************

    def start_show(self):
        # initial direction from parent show

        self.kickback_for_next_track=self.parent_kickback_signal
        # print '\n\ninital KICKBACK from parent', self.kickback_for_next_track

        # start duration timer
        if self.show_timeout  != 0:
            # print 'set alarm ', self.show_timeout
            self.duration_timer = self.canvas.after(self.show_timeout*1000,self.show_timeout_stop)

        self.first_list=True

        # and start the first list of the show
        self.wait_for_trigger()

    def wait_for_trigger(self):

        # wait for trigger sets the state to waiting so that trigger events can do a start_list.
        self.state='waiting'

        self.mon.log(self,self.show_params['show-ref']+ ' '+ str(self.show_id)+ ": Waiting for trigger: "+ self.show_params['trigger-start-type'])


        if self.show_params['trigger-start-type'] == "input":

            #close the previous track to display admin message
            Show.base_shuffle(self)
            Show.base_track_ready_callback(self,False)
            Show.display_admin_message(self,self.show_params['trigger-wait-text'])

        elif self.show_params['trigger-start-type'] == "input-persist":
            if self.first_list ==True:
                #first time through track list so play the track without waiting to get to end.
                self.first_list=False
                self.start_list()
            else:
                #wait for trigger while displaying previous track
                pass

        elif self.show_params['trigger-start-type'] == "start":
            # don't close the previous track to give seamless repeat of the show
            self.start_list()

        else:
            self.mon.err(self,"Unknown trigger: "+ self.show_params['trigger-start-type'])
            self.end('error',"Unknown trigger: "+ self.show_params['trigger-start-type'])

    def start_list(self):
        # starts the list or any repeat having waited for trigger first.
        self.state='playing'

        # initialise track counter for the list
        self.track_count=0

        # start interval timer
        self.interval_timer_signal = False
        if self.interval != 0:
            self.interval_timer=self.canvas.after(self.interval*1000,self.end_interval_timer)

        #get rid of previous track in order to display the empty message
        if self.medialist.display_length() == 0:
            Show.base_shuffle(self)
            Show.base_track_ready_callback(self,False)
            Show.display_admin_message(self,self.show_params['empty-text'])
            self.wait_for_not_empty()
        else:
            self.not_empty()

    def wait_for_not_empty(self):
        if self.medialist.display_length()==0:
            # list is empty retry after 5 secs
            self.canvas.after(5000,self.wait_for_not_empty)
        else:
            Show.delete_admin_message(self)
            self.not_empty()

    def not_empty(self):
        #get first or last track depending on direction
        # print 'use direction for start or end of list', self.kickback_for_next_track
        if self.kickback_for_next_track is True:
            self.medialist.finish()
        else:
            self.medialist.start()
        self.start_load_show_loop(self.medialist.selected_track())

        
