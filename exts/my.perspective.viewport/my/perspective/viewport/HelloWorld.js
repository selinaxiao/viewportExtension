var oU = preferences.rulerUnits
//change unit of pix
preferences.rulerUnits = Units.INCHES


//change resolution
var docRef = app.documents.add(2,4)

var artLayerRef = docRef.artLayers.add()

artLayerRef.kind = LayerKind.TEXT

//add layer with the image
var textItemRef = artLayerRef.textItem
textItemRef.contents = "Hello, World!"

docRef = null
artLayerRef = null
textItemRef = null

app.preferences.rulerUnits = oU