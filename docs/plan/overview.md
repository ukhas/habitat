% habitat overview
%
%

# habitat overview

## Users:

-   **People listening at home**: constitute the bulk of the
    distributed network nodes, have reasonably reliable internet
    connectivity and are uploading telemetry strings. They want to see
    a map with all known points on it, as well as compete for points in
    a points game
-   **Chase cars:** usually only one or two per launch, but desire
    the latest position information when they have connectivity.
    Internet access patchy, usually via 3G networks which means
    restricted bandwidth and availability. Often upload telemetry
    strings, but will need to be able to spool them locally for
    retransmission when connectivity is established. Portable,
    no-network-required maps showing last known points a major plus.
-   **People heading out to listen**: rare but main requirement
    will be to spool messages for transmission when internet is
    available
-   **Non-listeners:** people who just want to see the balloon's
    (and chase car's/cars') progress on the map, without installing any
    extra software
-   **Phones**: could decode RTTY and upload telem, or serve as
    chase car locators, but installing extra custom software is hard
    and there are a wide range of platforms that would need targetting.
    an HTTP access point for them to send data to would be easiest for
    the creators of the primary programs to use, and a web interface
    could provide return data (e.g., via google maps)
-   **Servers**: want all data from everyone, for archiving,
    serving as maps, analysing, awarding points, et cetera. loads of
    bandwidth, very reliable internet and uptime. can function as
    central network nodes

## Homepage

a static html file; fullscreen map, includes these independent JS
libs

-   **map abstraction layer**
    -   OS
    -   OSM
    -   GMaps
    -   creates a 'Map Tracks' window showing all the current tracks
        that have been added to the map, e.g. from predictor, archives,
        current track, chase cars &c, with options to hide or remove

-   **UI abstraction layer**
    -   jQuery UI: floaty UI windows (like the ones in the v2
        predictor) library; each of the below will create its own window.
        Must be minimisable.
    -   UI for phones
    -   etc.

-   **mission control**
    -   downloads a file by ajax (and perhaps updates periodically)
        which specifies **flights** by a time range (24 hours, or more for
        floaters) and one or more callsigns. Anything that doesn't match
        goes into the "sandbox" track group (which clears every 24 hours @
        UTC 0:00 ?) for people to test with w/o spamming up the homepage.
    -   The windows for the tracker, predictor, and archive can be
        default minimised or open depending on what's happening \*now\*, so
        if during a flight someone goes to the homepage they get what they
        (probably) want there and then

-   **archive client**
    -   Uses the mission control list to find out what's happening;
        list of old and in-progress missions
    -   in the floaty UI box you can choose which tracks you want to
        show.
    -   Loads data
    -   If flight is in progress, streams (new only) data (by ajax or
        flash socket for push rather than poll) and plots the points on
        map. Asks the server to only send it the tracks that it's
        interested in.
    -   Hiding indvidual tracks in the "group" (see mission control)
        could be done by the map tracks window (?)

-   **predictor client**
    -   same interface as current "v2" predictor; put stuff in, press
        button, get prediction

-   notes:
    -   All of these separate libs should be able to plot data on the
        map independently and simultaneously
    -   In flight predictions: spacenear updates a prediction as the
        flight goes. (Since the predictor caches predictions we could say,
        request a new one every 5 minutes and "implement" this feature
        totally in Javascript with a call to the predictor lib from the
        tracker lib).


## Current names & Definitions

*Currently*, there are many **listeners** at home, or there may be
a listener in a **chase car** (or boat?). The listeners use the
**dl-client** software which may be dl-fldigi. dl stands for
**distributed listener** and is the name for the system
encompassing the dl-client, the many listeners, and the
**dl-server or dlistener** (which sometimes, is confusingly
referred to simply as **listen or listener**). The distributed
listener could be thought of to include the tracker, though really
the listener is a system which feeds into the tracker. The
**tracker** collects points (although the strings are parsed by the
listener) in a database, and serves ajax requests for data made by
people using the html **map**.

## Proposed habitat definitions:

-   **payloads** encode *payload data* into a **telemetry string**
    and send them out as a **transmission**
-   **payload data** contains information from the *payload* such
    as position, time and sensor information
-   **messages** contain
    -   the source *listener's identifier*
    -   a message type, which is one of:
        -   *received telemetry string*
        -   *listener information*
        -   *listener telemetry string* (from chase car gps, for example)
        -   *telemetry data*


-   there are many **listeners**, which comprise
    -   some sort of unique **identifier**
    -   **listener information** (metadata such as callsign and
        location)
    -   a **radio** - receives the *transmission*
    -   **decoder** (a class of which fldigi is one)
        -   decodes the *transmission* to a sequence of chars
        -   splits the sequence of chars into *telemetry strings* by
            looking for start and end markers.
        -   since noise creates imperfections in the received data, there
            are many **received telemetry strings** for each *telemetry string*
            transmitted by the payload

    -   **uploader** - transmits (potentially via HTTP POST) this
        information, encapsulated in *messages,* to a *message server*,
        along with the *listener*'s *listener information*
        -   every single *received telemetry string*
        -   *listener telemetry strings* from a local gps (eg. chase car)
        -   periodically, *listener information*
        -   if the listener is static, periodically, a
            *listener telemetry string* for their location is sent


-   **message server** is one of these
    -   **master message server** on the *master server*
        -   gets *messages* from an *uploader*, a *spooler* or a
            *dummy message server* (although all three use the same HTTP POST
            interface/protocol) and
            -   pushes each *message* to the relevant sink


    -   **spooler** on localhost
        -   gets *messages* from a localhost *uploader* and attempts to
            forward each *message* to the *master message server*. If it fails
            to receive an acknowledgement, it stores the *message* for later
            retry.

    -   **dummy message server** on localhost
        -   gets *messages* from a localhost *uploader* and
            -   pushes each *message* to the relevant sink
            -   attempts to forward each *message* to the
                *master message server*. If it fails to receive an acknowledgement,
                it stores the *message* for later retry.

        -   periodically attempts to contact the *archive* on the
            *master server* in order to download all of the *messages* that the
            *master server* has. It then
            -   pushes each *message* to the relevant sink
            -   (NB: this may cause duplicates; localhost-\>master-\>localhost,
                but this is known)



-   **raw sinks**
    -   accept *messages* of type *received telemetry strings*
    -   must tolerate duplicates
    -   **repairer** attempts to correct an invalid message and
        reinserts it into the local *message server* if possible
    -   **raw logger** stores the *received telemetry strings*
    -   **parser** decodes the *received telemetry string* into
        *telemetry data* only if the checksum is correct, and sends a
        *telemetry data -* *message* to the local *message server*

-   **parsed sinks**
    -   accept *messages* of types *telemetry data,*
        *listener telemetry strings* and *listener information*
    -   the **archive**
        -   stores *telemetry data*
        -   stores *listener telemetry strings*
        -   stores *listener information*
        -   instead of duplicates, against each *telemetry data* item, it
            stores a list of *listener identifiers* and has the ability to
            recall what their most recent *listener telemetry string* was at
            the time when the *listener* uploaded their copy
        -   if not installed on the *master server*, it periodically
            attempts to contact the *archive* on the *master server* in order
            to download all of the de-duplicated data it has, and merge it into
            its own data

    -   **points game** awards points to *listener identifiers*
        (possibly based on their distance to the payload, as determined
        from their most recent *listener telemetry string*)

-   **mission control** contains a list of **flights**, defined by
    a time range, and one or more callsigns, which may be the callsigns
    of payloads or chase cars
-   *listeners* and spectators will use the **map** web application
    -   some may be using a copy served by a HTTP daemon on localhost,
        and some using one on the *master server.* The machine that runs
        the HTTP server they are using is hereafter referred to as the
        **web application server**
    -   the **predictor client** contacts the **predictor binary**
        running on the *web application server* in order to display
        predictions on the *map*
    -   the **archive client** contacts the **archive** running on the
        *web application server* in order to download and display all
        information from a *flight* on the map. if *mission control*
        reports that the flight is currently in progress, it will stream or
        poll for that information
    -   the *points game client* and *mission control client*
        periodically download data from the *points game* or
        *mission control*, respectively

-   notes:
    -   the *master server* in our setup will typically be nessie
    -   that some of these may be implemented in a single process (for
        example, **dl-fldigi** currently is a single process containing a
        modified fldigi and a builtin *uploader*)
    -   some *messages* by design will contain duplicated information
        from different *listener*, or perhaps (due to replication) from the
        same *listener*
    -   the *points game* and the *dummy message server* could really
        do with better names
    -   We've looked at the possible users and if they require one of
        the "tools", their use case will probably require a message daemon
        install anyway. Therefore the communication between the listener
        and the other tools doesn't have to be HTTP or even IP; could be a
        unix socket (which might be a bit nicer).
    -   The tool that would be concerned about replication or internet
        reliability is the listener. We could use an existing DB or write
        our own; however, if we do use an existing one (SQL or NoSQL) using
        the built-in replication may cause problems. For starters, users
        would have to be authenticated with it in order to replicate it.
        The message system we want to create is append-only; but most DBs
        are not. We probably - either way - would have to create a frontend
        API which is used by listeners to add data to the listener tool but
        also by the chase car when it wants to bring itself up to speed.
        The operations (put and get) are exactly the same.


habitat plan – Copyright Daniel Richman and Adam Greig 2010
This work is licensed under a Creative Commons
Attribution-NonCommerical-ShareAlike 2.0 UK:England & Wales License

[http://creativecommons.org/licenses/by-nc-sa/2.0/uk/](http://creativecommons.org/licenses/by-nc-sa/2.0/uk/)



