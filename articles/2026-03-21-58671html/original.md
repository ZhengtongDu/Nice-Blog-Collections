# You Should Use /tmp/ More

# You Should Use /tmp/ More

**2025-02-10**

Digging around your file system is probably not many's idea of fun, content to live in your `/home/` directory and that be that. But there can be benefit in doing some exploring, seeing what other functionality your machine offers, and trying to think about them in new contexts.

One directory that I think should really get more attention and one that I keep finding new use-cases for is the [`/tmp/`](https://refspecs.linuxfoundation.org/FHS_3.0/fhs/ch03s18.html) directory. Intended for temporary files, `/tmp/` is typically where 'stuff' that a program doesn't need in the long-term goes: temporary backups of files you're working on, your browser caching some content, a holding place for in-progress updates. `/tmp/` also has the unique benefit that it is cleared whenever your machine is reset - it is temporary after all.

`/tmp/` _is_ largely intended as a space for software to do 'stuff' like those operations already mentioned, but there's nothing to stop you using it for your own purposes. And so, over the past few years, I've really integrated `/tmp/` into regular use to surprising effect.

One of the most powerful uses I've found is setting my downloads folder to `/tmp/`. It's largely been my experience and from seeing others that the default 'Downloads' folder seems to act as a rubbish bin that never gets emptied. Gigabytes of stuff just sitting in a folder entirely forgotten about: Why do I still have an ISO file for Ubuntu 12.04 from over a decade ago? Why are projects that finished years ago still sitting here? `.exes` that seemed to have lingered despite me using Linux for over a decade at this point.

It's a fascinating time capsule to dig through your own downloads folder but you probably should not have to stumble across files like it's an excavation. `/tmp/` makes for an excellent place to send your downloads instead. 

Simple stuff - Printing a packing label? Send it to `/tmp/`, print it, and then forget it rather than it lingering in your downloads. Got an image you want to use in a quick project in [GIMP](https://www.gimp.org)? Throw it in `/tmp/` rather than wondering why I have a seemingly random JPEG years from now. 

Making use of `/tmp/` has also been surprisingly good as part of my general workflow for more 'serious' work. Particularly when doing research, I might need to dig through hundreds of PDFs of research papers, I can just have all of them download to my `/tmp/` folder and just start working through them. There's no risk of them getting dumped in a folder and forgotten and no risk of them taking up space after they're done. Working on a dataset for a project? Put it in `/tmp/`. You can just download the latest version when you come back to it. No steadily accumulating 'v1', 'v2', 'v2_final' etc.

Quick TODOs and other scratchpad-like content is also a perfect fit for `/tmp/`. I used to just throw a note in my home directory like 'monday.md' or '2023-03-05.txt' with whatever needed done on that day. `/tmp/` continues to be a good fit for this. I can start the day by putting a text file in `/tmp/`, filling it up with what needs done, and then have it cleared away when I shut down my machine. 

I use LaTeX a lot which produces a lot of files when compiling documents: a file for your table of contents, a file for your bibliography, an intermediary DVI file on the way to PDF, the resultant PDF etc. These _are_ fine and keeping them readily available can speed up future compilations but more often than not I really don't need them. So, I can add the following to `pdflatex` and just put all the temporary files where they belong:

` pdflatex -output-directory=/tmp/ `

This does put the finished PDF into `/tmp/` as well but usually I only want to retain the source code and will just compile the document as needed - saving on space.

While just about any of the ideas I've suggested here _could_ be done in a regular file system with decent organisation, when working in `/tmp/` it is hard to ignore the gentle nudge that everything not saved will be lost. Making heavy use of `/tmp/` forces you to make decisions surrounding what actually matters on your machine: keeping a copy of everything that's ever happened on your machine or keeping what you actually need in long-term storage while treating everything else as disposable? It's a self-tidying workspace without the annoyance of a random file that just ends up sitting around.

`/tmp/` offers a lot of surprising applications that stem purely from the fact that it's temporary. It lets you make better decisions surrounding what actually needs stored longer term and what can be discarded. It helps keep check of your storage usage by automatically deleting files that you don't need. It keeps your overall file system tidy by inherently getting rid of stuff you don't need. 

So consider trying `/tmp/`, if it isn't for you, you can start fresh after the next reboot.