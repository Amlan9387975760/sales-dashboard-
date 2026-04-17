// Paste this entire code into script.google.com
// Then click Deploy → New Deployment → Web App → Anyone → Deploy

const SHEET_ID = "1ZPYxiNnJ6xCACg86YorR3899wIoyUb3SUG5MvNf7yPo";
const HEADERS  = ["ID", "Company Name", "Demo Start Date", "Challenge Type", "Status", "Sales Rep", "Notes"];

function getSheet() {
  var ss = SpreadsheetApp.openById(SHEET_ID);
  var ws = ss.getSheets()[0];
  if (ws.getLastRow() === 0 || ws.getRange(1,1).getValue() !== "ID") {
    ws.clearContents();
    ws.appendRow(HEADERS);
  }
  return ws;
}

function doGet(e) {
  var action = e.parameter.action;
  var ws = getSheet();
  if (action === "getAll") {
    var rows = ws.getDataRange().getValues();
    var headers = rows[0];
    var data = rows.slice(1).map(function(row) {
      var obj = {};
      headers.forEach(function(h, i) { obj[h] = row[i]; });
      return obj;
    });
    return ContentService.createTextOutput(JSON.stringify(data))
      .setMimeType(ContentService.MimeType.JSON);
  }
  return ContentService.createTextOutput("[]").setMimeType(ContentService.MimeType.JSON);
}

function doPost(e) {
  var data = JSON.parse(e.postData.contents);
  var ws   = getSheet();
  var action = data.action;

  if (action === "add") {
    var rows = ws.getDataRange().getValues();
    var maxId = rows.slice(1).reduce(function(m,r){ return Math.max(m, Number(r[0])||0); }, 0);
    ws.appendRow([maxId+1, data.company||"", data.demo_date||"", data.challenge||"", data.status||"", data.sales_rep||"", data.notes||""]);
    return json({success:true});
  }

  if (action === "update") {
    var ids = ws.getRange(1,1,ws.getLastRow(),1).getValues().flat().map(String);
    var row = ids.indexOf(String(data.id)) + 1;
    if (row > 0) {
      ws.getRange(row, HEADERS.indexOf("Status")+1).setValue(data.status);
      if (data.reason) {
        var notesCell = ws.getRange(row, HEADERS.indexOf("Notes")+1);
        var old = notesCell.getValue() || "";
        var today = new Date().toISOString().slice(0,10);
        var oldStatus = ws.getRange(row, HEADERS.indexOf("Status")+1).getValue();
        notesCell.setValue((old + " | ["+today+"] "+oldStatus+"→"+data.status+": "+data.reason).replace(/^\s*\|\s*/,""));
      }
    }
    return json({success:true});
  }

  if (action === "delete") {
    var ids = ws.getRange(1,1,ws.getLastRow(),1).getValues().flat().map(String);
    var row = ids.indexOf(String(data.id)) + 1;
    if (row > 0) ws.deleteRow(row);
    return json({success:true});
  }

  return json({success:false});
}

function json(obj) {
  return ContentService.createTextOutput(JSON.stringify(obj))
    .setMimeType(ContentService.MimeType.JSON);
}
