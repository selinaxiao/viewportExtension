var theFolder = Folder.selectDialog("select folder");

if (theFolder) {

    var theFiles = theFolder.getFiles(/\.(jpg|tif|eps|psd)$/i);

    for (var m = 0; m < theFiles.length; m++) {

        app.open(File(theFiles))

    }
}

doc = app.activeDocument;

doc.changeMode(ChangeMode.RGB);

var thumbDim = 1280; // the dimension of the square

// crop to a big square, conditionally, based on dimensions

if (doc.height > doc.width) {

    doc.resizeCanvas(doc.width,doc.width,AnchorPosition.TOPCENTER);

}

else {

    doc.resizeCanvas(doc.height,doc.height,AnchorPosition.MIDDLECENTER);

}

// specify that our units are in pixels, via creation of a UnitValue object

doc.resizeImage(UnitValue(thumbDim,"px"),null,null,ResampleMethod.BICUBIC);
// our web export options

var options = new ExportOptionsSaveForWeb();

options.quality = 100;

options.format = SaveDocumentType.PNG;

options.optimized = true;

var newName = 'web-'+doc.name+'.png';

doc.exportDocument(File(doc.path+'/'+newName),ExportType.SAVEFORWEB,options);
