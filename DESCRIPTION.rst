har2python
==========

How to get har archive? (http://en.wikipedia.org/wiki/.har)

1) Chrome
2) F12
3) Network
4) Preserve log (checked)
5) go over some sites
6) click right
7) Save as HAR with content

examples
-----

::

    python har2python data_1.har data_2.har

::

    python har2python data_1.har data_2.har --debug

TODO
-----------------

- Auto detect which request are needed (many times simulate process, checking return codes, or response body content)
