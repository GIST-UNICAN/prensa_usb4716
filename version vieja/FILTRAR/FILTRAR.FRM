VERSION 5.00
Begin VB.Form FILTRAR 
   ClientHeight    =   6612
   ClientLeft      =   48
   ClientTop       =   336
   ClientWidth     =   9588
   LinkTopic       =   "Form1"
   ScaleHeight     =   6612
   ScaleWidth      =   9588
   StartUpPosition =   3  'Windows Default
   Begin VB.CommandButton Command2 
      Caption         =   "DIBUJAR"
      BeginProperty Font 
         Name            =   "MS Sans Serif"
         Size            =   12
         Charset         =   0
         Weight          =   700
         Underline       =   0   'False
         Italic          =   0   'False
         Strikethrough   =   0   'False
      EndProperty
      Height          =   852
      Left            =   360
      TabIndex        =   5
      Top             =   5400
      Width           =   2892
   End
   Begin VB.FileListBox archivo 
      Height          =   2376
      Left            =   120
      TabIndex        =   4
      Top             =   2520
      Width           =   9132
   End
   Begin VB.DirListBox carpeta 
      Height          =   2232
      Left            =   4200
      TabIndex        =   3
      Top             =   120
      Width           =   5172
   End
   Begin VB.DriveListBox disco 
      Height          =   288
      Left            =   360
      TabIndex        =   2
      Top             =   240
      Width           =   3012
   End
   Begin VB.TextBox VELOCIDADENSAYO 
      Alignment       =   2  'Center
      BeginProperty Font 
         Name            =   "MS Sans Serif"
         Size            =   9.6
         Charset         =   0
         Weight          =   700
         Underline       =   0   'False
         Italic          =   0   'False
         Strikethrough   =   0   'False
      EndProperty
      Height          =   348
      Left            =   4800
      TabIndex        =   0
      Top             =   5880
      Width           =   1932
   End
   Begin VB.Label Label3 
      Alignment       =   2  'Center
      Caption         =   "VELOCIDAD DE ENSAYO (MM/MIN)"
      BeginProperty Font 
         Name            =   "MS Sans Serif"
         Size            =   7.8
         Charset         =   0
         Weight          =   700
         Underline       =   0   'False
         Italic          =   0   'False
         Strikethrough   =   0   'False
      EndProperty
      Height          =   492
      Left            =   4320
      TabIndex        =   1
      Top             =   5160
      Width           =   2892
   End
End
Attribute VB_Name = "FILTRAR"
Attribute VB_GlobalNameSpace = False
Attribute VB_Creatable = False
Attribute VB_PredeclaredId = True
Attribute VB_Exposed = False
Dim carga(1 To 5000) As Double
Dim CARGABUENA(1 To 5000) As Double
Dim deformacion(1 To 5000) As Double
Dim DEFORMACIONBUENA(1 To 5000) As Double
Dim TIEMPO(1 To 5000) As Double
Dim CORRELACION(1 To 5000) As Double
Dim DEFREF(1 To 5000) As Integer
Dim CARGAREF(1 To 5000) As Integer
Dim RESIDUO(5000) As Double
Dim LINEADATOS As String
Dim primero, segundo As Integer
Dim t As Double
Dim REFERENCIA(1 To 5000) As Integer
Dim cargamaxima, cargainicio, cargafinal
Dim TIEMPOINICIAL As Long
Dim nregistros, puntoinicio, puntofinal As Integer
Dim asterisco As String
Dim I, I1, J As Integer
Dim TIEMP As Long
Dim fichero, salida, archivoseleccionado As String
Dim CONTADOR As Integer
Dim CUADRADOS As Double
Dim VALORMEDIO As Double
Dim TARA As Integer
Dim INICIO, FINAL, MEDIO, INDICE, POSICION, VALIDOS, VALIDOSD, FALLOS As Integer
Dim M11, M12, M21, T1, T2, A, B As Double
Dim M22 As Double

Private Sub archivo_Click()
archivoseleccionado = archivo.Path
End Sub

Private Sub carpeta_Change()
    archivo.Path = carpeta.Path
End Sub

Private Sub Command1_Click()

'ABRO FICHERO DISCO Y LEO DATOS
fichero = archivoseleccionado + "\" + archivo
Open fichero For Input As #1
Line Input #1, LINEADATOS
'Input #1, DEFORMACION(1), CARGA(1), TIEMPOINICIAL
primero = InStr(1, LINEADATOS, "*")
segundo = InStr(primero + 1, LINEADATOS, "*")
deformacion(1) = Val(Mid$(LINEADATOS, 1, primero - 1))
carga(1) = Val(Mid$(LINEADATOS, primero + 1, segundo - primero - 1))
TIEMPOINICIAL = Val(Mid$(LINEADATOS, segundo + 1, Len(LINEADATOS) - segungo))
TIEMPO(1) = 0
I = 0
While Not EOF(1)
    I = I + 1
    Line Input #1, LINEADATOS
    primero = InStr(1, LINEADATOS, "*")
    segundo = InStr(primero + 1, LINEADATOS, "*")
    deformacion(I) = Val(Mid$(LINEADATOS, 1, primero - 1))
    carga(I) = Val(Mid$(LINEADATOS, primero + 1, segundo - primero - 1))
    t = Mid$(LINEADATOS, segundo + 1, Len(LINEADATOS) - segundo)
    TIEMPO(I) = t - TIEMPOINICIAL
Wend

registros = I
Close
nregistros = I




' BUSCO CARGA MAXIMA

cargamaxima = CARGABUENA(1)

For I = 1 To VALIDOS
    If CARGABUENA(I) > cargamaxima Then cargamaxima = CARGABUENA(I)
Next I


cargainicio = 0.05 * cargamaxima
cargafinal = 0.95 * cargamaxima

'FileSystemObject.Delete "c:\arcchivos de pregrama\MARSHALL2007\FILTRAR\AUXILIAR"

Open "C:\marshall_2007\DIBUJAR\auxiliar" For Output As 1
    For I = 1 To registros
       Print #1, 100 * Int(deformacion(I)), carga(I)
    Next I
    Close
    RetVal = Shell("C:\Archivos de programa\Microsoft Office\Office10\EXCEL.EXE C:\MARSHALL_2007\dibujar\dibuja_datos.xls", 1)

End Sub

Private Sub r_Click()

End Sub

Private Sub Text1_Change()

End Sub

Private Sub Dir1_Change()

End Sub

Private Sub Command2_Click()
'ABRO FICHERO DISCO Y LEO DATOS
fichero = archivoseleccionado + "\" + archivo
Open fichero For Input As #1
Line Input #1, LINEADATOS
'Input #1, DEFORMACION(1), CARGA(1), TIEMPOINICIAL
primero = InStr(1, LINEADATOS, "*")
segundo = InStr(primero + 1, LINEADATOS, "*")
deformacion(1) = Val(Mid$(LINEADATOS, 1, primero - 1))
carga(1) = Val(Mid$(LINEADATOS, primero + 1, segundo - primero - 1))
TIEMPOINICIAL = Val(Mid$(LINEADATOS, segundo + 1, Len(LINEADATOS) - segungo))
TIEMPO(1) = 0
I = 0
While Not EOF(1)
    I = I + 1
    Line Input #1, LINEADATOS
    primero = InStr(1, LINEADATOS, "*")
    segundo = InStr(primero + 1, LINEADATOS, "*")
    deformacion(I) = Val(Mid$(LINEADATOS, 1, primero - 1))
    carga(I) = Val(Mid$(LINEADATOS, primero + 1, segundo - primero - 1))
    t = Mid$(LINEADATOS, segundo + 1, Len(LINEADATOS) - segundo)
    TIEMPO(I) = t - TIEMPOINICIAL
Wend

registros = I
Close
Open "C:\marshall_2007\DIBUJAR\auxiliar" For Output As 1
    For I = 1 To registros
       Print #1, 100 * Int(deformacion(I)), carga(I)
    Next I
    Close
    RetVal = Shell("C:\Archivos de programa\Microsoft Office\Office11\EXCEL.EXE C:\MARSHALL_2007\dibujar\dibuja_datos.xls", 1)

End Sub

Private Sub disco_Change()
    On Error GoTo salta
    Dim respuesta As Integer
    carpeta.Path = disco.Drive
    Exit Sub
salta:
    respuesta = MsgBox(Err.Description, 5, "No hay disco")
    If respuesta = 4 Then Resume
End Sub

Private Sub NOMBREFICHERO_Change()

End Sub







Private Sub valen_Change()

End Sub

