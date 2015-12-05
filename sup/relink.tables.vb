Option Compare Database

Sub relate_tables()
    
    Dim db As DAO.Database
    Dim tdf1 As DAO.TableDef
    Dim tdf2 As DAO.TableDef
    Dim rels As DAO.Relations
    Dim rel As DAO.Relation
    Dim rs As Recordset
     
    Set db = CurrentDb
    Set rels = db.Relations
    
    Set rs = db.OpenRecordset("SELECT from_table, from_field, to_table, to_field, True as optional FROM _LOOKUPS")
    
    Do While Not rs.EOF
        tdf = db.TableDefs(rs!from_table)
    
    
        Set tdf1 = db.TableDefs(rs!from_table)
        Set tdf2 = db.TableDefs(rs!to_table)
         
        relname = rs!from_table & rs!to_table
         
        For Each rel In rels
            If rel.Name = relname Then
                rels.Delete (relname)
            End If
        Next
         
        Set rel = db.CreateRelation(relname, tdf1.Name, tdf2.Name, dbRelationDontEnforce) ' , dbRelationUpdateCascade)
         
        rel.Fields.Append rel.CreateField(rs!from_field)
        rel.Fields(rs!from_field).ForeignName = rs!to_field
        rels.Append rel
        
        rs.MoveNext
    Loop

    MsgBox "Tables linked"

End Sub

