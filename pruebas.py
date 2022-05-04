from appJar import gui

def opt_changed(opt):
    print(app.getOptionBox("optionbox"))

def lst_changed(lst):
    print(app.getListBox("list")[0])

def press(btn):
    if btn == "Cancel":
        app.stop()
    elif btn == "Show":
        list_select()
    else:
        print('not defined yet')

def list_select():
    app.infoBox("Info", "You selected " + app.getOptionBox("optionbox") + "\nBrowsing " + app.getListBox("list")[0])

app = gui("Database Editor", "500x500")
app.addOptionBox("optionbox", ["a", "b", "c", "d"])
app.addListBox("list", ["one", "two", "three", "four"])

app.setOptionBoxChangeFunction("optionbox", opt_changed)
app.setListBoxChangeFunction("list", lst_changed)

app.addButtons(["Show", "Cancel"], press)
app.go()