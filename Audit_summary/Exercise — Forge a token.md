### Record 

Step 1
- What does the payload say your role is?
  student
- Was the payload encrypted, or could you read it straight away?
  Read straight away (base64)

Step 4
- Did you get bob's note, or an error?
  bob's note
- What is bob's grade?
  12.6
- What is bob's comment?
  Solid work, keep it up.

Step 5
- What is NotesApp's signing secret?
  s3cr3t

Step 6
- Did the signed forged token work?
  Yes
- Would "reject alg:none" have stopped it?
  No

---

### Four lines finding

FORGED-TOKEN FINDING — NotesApp flaw #4 (auth)
What I read: bob's grade (12.6) and comment, via /api/notes/3
Break 1: a JWT with "alg":"none" and no signature; role set to "teacher"
Break 2: cracked the HS256 secret (s3cr3t) from a wordlist; signed a real teacher token
Why it worked: the server let the TOKEN choose how to verify, AND its secret was guessable