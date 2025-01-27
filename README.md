# ToDo

# shiny4Python
Create a shiny for Python app.  You can create both a `site` or full app based on `FastAPI`.

In these lines we:
- Install `shiny` & `shinylive`
- Create a Hello world app
- Run the [app](https://shiny.rstudio.com/py/docs/deploy.html) based on the `FastAPI`
- Create as a [static website](https://shiny.rstudio.com/py/docs/shinylive.html) with `WebAssembly`

```
pip install shiny
pip install shinylive
shiny create .
shiny run 
shinylive export . docs
```

..........rollback to put on top.  conflict simplify to just alert and give option to reload or save local



`Note:` We output the website to `docs` to host on a Github Page


![image](https://user-images.githubusercontent.com/33904170/215349262-68b36efa-ceff-40ea-ae80-052303a7258b.png)
