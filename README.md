# openscad_offliner
Download OpenSCAD online documentation for offline reading.

Require: python 3, BeautifulSoup

Updated on 2019, Sometime in May:

Did some stuff - maybe it works? I can't actually remember what I did or why other than it is now python3 based
Should work similarly to before.
See the source.

----

Updated on 2016, March 20th:

  * Major fix for bug believed to be a cross-platform issue. The original version, which is developed in Linux, is saved as openscad_offliner_2015.py. It is made to work in Windows in the current version.
  * Include openscad_docs.zip. Users don't need to run the python script, unless a most recent copy is needed.
  
Usage:

		1) Save this file in folder x.
		2) In folder x, type: 
			
			  python openscad_offliner.py 

		   or to save log to a file:  
	
			  python openscad_offliner.py > openscad_offliner.log

		All web pages will be saved in x/openscad_docs, 
		and all images in x/openscad_docs/imgs  

Note: 

    1) All html pages are stored in dir_docs (default: openscad_docs)
    2) All images are stored in dir_imgs (default: openscad_docs/imgs)
    3) All OpenSCAD-unrelated stuff, like wiki menu, etc, are removed
    4) All wiki warnings sign are removed
    5) Search box is hidden. There might be a way (i.e., javascript) to 
       search the doc but we leave that to the future.
