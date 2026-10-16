# encoding: utf-8

# This Server class connects against Stellar.
# The monitor URL in the setup should be something like
# http://stellar.example.com:30007
#
# Release Notes:

import sys
import urllib.request
import urllib.parse
import urllib.error
import pprint
import json

from datetime import datetime, timedelta, timezone
import dateutil.parser

from Nagstamon.Config import conf
from Nagstamon.Objects import (GenericHost,
                               GenericService,
                               Result)
from Nagstamon.Servers.Generic import GenericServer
from Nagstamon.Helpers import webbrowser_open


class StellarService(GenericService):
    """
    add Stellar specific service property to generic service class
    """
    service_object_id = ""
    labels = {}


class StellarServer(GenericServer):
    """
    special treatment for Stellar API
    """
    TYPE = 'Stellar'

    # Stellar actions are limited to visiting the monitor for now
    MENU_ACTIONS = ['Monitor']
    BROWSER_URLS = {
        'monitor':  '$MONITOR$/dashboards',
        'hosts':    '$MONITOR$/targets',
        'services': '$MONITOR$/alert-cur-events',
        'history':  '$MONITOR$/alert-his-events'
    }

    API_PATH_ALERTS = "/v1/n9e/alert-cur-events?limit=100"

    def init_HTTP(self):
        """
        things to do if HTTP is not initialized
        """
        GenericServer.init_HTTP(self)

        # prepare for JSON
        self.session.headers.update({'Accept': 'application/json',
                                     'Content-Type': 'application/json'})

    def init_config(self):
        """
        dummy init_config, called at thread start
        """
        pass

    def get_start_end(self, host):
        """
        Set a default of starttime of "now" and endtime is "now + 24 hours"
        directly from web interface
        """
        start = datetime.now()
        end = datetime.now() + timedelta(hours=24)

        return (str(start.strftime("%Y-%m-%d %H:%M:%S")),
                str(end.strftime("%Y-%m-%d %H:%M:%S")))

    def _get_duration(self, timestring):
        """
        calculates the duration (delta) from Stellar' activeAt (ISO8601
        format) until now an returns a human friendly string
        """
        time_object = dateutil.parser.parse(timestring)
        duration = datetime.now(timezone.utc) - time_object
        h = int(duration.seconds / 3600)
        m = int(duration.seconds % 3600 / 60)
        s = int(duration.seconds % 60)
        if duration.days > 0:
            return "%sd %sh %02dm %02ds" % (duration.days, h, m, s)
        elif h > 0:
            return "%sh %02dm %02ds" % (h, m, s)
        elif m > 0:
            return "%02dm %02ds" % (m, s)
        else:
            return "%02ds" % (s)

    def _set_downtime(self, host, service, author, comment, fixed, start_time,
                      end_time, hours, minutes):
        """
        to be implemented in a future release
        """
        pass

    def _get_status(self):
        """
        Get status from Stellar Server
        """
        # get all alerts from the API server
        try:
            result = self.FetchURL(self.monitor_url + self.API_PATH_ALERTS,
                                   giveback="raw")
            # transform JSON to Python data structure
            data = json.loads(result.result)
            # get error and status code 
            error = result.error
            status_code = result.status_code
            # check if any error occured
            errors_occured = self.check_for_error(data, error, status_code)
            if errors_occured is not None:
                return(errors_occured)
            if conf.debug_mode:
                self.Debug(server=self.get_name(),
                           debug="Fetched JSON: " + pprint.pformat(data))

            #for alert in data["data"]["alerts"]:
            for alert in data["dat"]["list"]:
                if conf.debug_mode:
                    self.Debug(
                        server=self.get_name(),
                        debug="Processing Alert: " + pprint.pformat(alert)
                    )

                #labels = alert.get("labels", {})

                # skip alerts with none severity
                #severity = alert.get("severity", "UNKNOWN").upper()
                # map Stellar severity to Alertmanager severity

                LEVEL_DICT = {
                '1': 'critical',
                '2': 'warning',
                '3': 'information',
                '0': 'NONE'
                }
                stellar_severity = alert.get("severity", 0)
                severity = LEVEL_DICT.get(str(stellar_severity), 'unknown').upper()

                if severity == "NONE":
                    continue

                # get hostname and servicename from alert

                #hostname = alert.get('id', 'unknown')
                #hostname = alert.get('cluster', 'unknown')
                hash_part = alert.get('hash', 'unknown')[-4:]
                hostname = f"{hash_part}-{alert.get('cluster', 'unknown')}"

                servicename = alert.get('rule_name', 'unknown')

                service = StellarService()
                service.host = str(hostname)
                service.name = servicename
                service.server = self.name
                service.status = severity
                service.last_check = "n/a"
                #service.attempt = alert.get("state", "firing")
                
                STATE_DICT = {
                '1': 'pending',
                '0': 'firing'
                }
                stellar_attempt = alert.get("status", 0)
                service.attempt = STATE_DICT.get(str(stellar_attempt), "firing")

                #service.duration = str(self._get_duration(alert["activeAt"]))
                # get first_trigger_time from alert and convert to human readable format
                first_trigger_time = alert.get("first_trigger_time", "N/A")

                if first_trigger_time :
                    first_trigger_time = datetime.fromtimestamp(int(first_trigger_time), tz=timezone.utc).isoformat()

                service.duration = str(self._get_duration(first_trigger_time))
                # annotations is a array of key-value pairs in Stellar 

                #status_information = ""
                #if annotations:
                #    first_annotation = next(iter(annotations.items()))
                #    status_information = first_annotation[1]
                #    service.status_information = status_information

                annotations = alert.get("annotations", {})
                status_information = ""
                for status_information_label in self.map_to_status_information.split(','):
                    if status_information_label in annotations:
                        status_information = annotations.get(status_information_label)
                        break
                service.status_information = status_information

                if hostname not in self.new_hosts:
                    # create new host and add service, if not already in list
                #    count = 0
                    self.new_hosts[hostname] = GenericHost()
                    # set hostname
                    self.new_hosts[hostname].name = str(hostname)
                    # set server name
                    self.new_hosts[hostname].server = self.name

                # add service dictionary to host.services
                #if hostname in self.new_hosts and servicename not in self.new_hosts[hostname].services:
                #    count = 0
                # Check if servicename already exists in the services dictionary
                #if hostname in self.new_hosts and servicename in self.new_hosts[hostname].services:
                #    count += 1

                #new_servicename = f"{servicename}-{str(count)}"
                #servicename = new_servicename
                self.new_hosts[hostname].services[servicename] = service

        except:
            # set checking flag back to False
            self.isChecking = False
            result, error = self.Error(sys.exc_info())
            return Result(result=result, error=error)

        # dummy return in case all is OK
        return Result()

    def open_monitor_webpage(self, host, service):
        """
        open monitor from tablewidget context menu
        """
        webbrowser_open('%s' % (self.monitor_url))

    def open_monitor(self, host, service=''):
        """
        open monitor for alert
        """
        url = '%s/graph?g0.range_input=1h&g0.expr=%s'
        url = url % (self.monitor_url,
                     urllib.parse.quote('ALERTS{alertname="%s"}' % service))
        webbrowser_open(url) 