har2python
==========

How to get har archive? (http://en.wikipedia.org/wiki/.har)

<ol>
<li>Chrome </li>
<li>F12 </li>
<li>Network </li>
<li>Preserve log (checked)</li>
<li>go over some sites</li>
<li>click right </li>
<li>Save as HAR with content</li>
</ol>
<p>
<code>
python har2python data_1.har data_2.har
</code>
</p>
<p>
<code>
python har2python data_1.har data_2.har --debug
</code>
</p>

TODO
____
<ol>
<li>
Auto detect which request are needed (many times simulate process, checking return codes, or response body content)¨¨
</li>
</ol>
