from appJar import gui

# the title of the button will be received as a parameter
def press(btn):
    if btn=="super":
        app.setButton("super","mola")
    if btn=="mola":
        app.setButton("Super")
    print(btn)

app=gui()
# 3 buttons, each calling the same function
app.addNamedButton("especial", "super", press)
app.addButton("One", press)
app.addButton("Two", press)
app.addButton("Three", press)
app.setSize(300,200)
app.go()