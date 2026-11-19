STORED XSS FIX — NotesApp flaw #10 closed

  Break:  comment on note 1 =  <script>alert('XSS by Eve')</script>
          opened as alice -> the alert ran; the comment was returned as raw
          <script> markup in Alice's dashboard

  Fix:    removed the {% autoescape false %} wrapper from dashboard.html
          and teacher.html

  Closed: same comment now shows as text -> the HTML source contains
          &lt;script&gt;...&lt;/script&gt;; no alert runs

  Real use still works: "score < 10 on part 1 & 2, see me" displays as
          ordinary text; special characters are escaped in the HTML source [x]