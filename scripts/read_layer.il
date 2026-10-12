/* Dump one layer's rectangles of one cellview to a text file on the remote host.
 *
 *   virtuoso-bridge load read_layer.il -p <profile> --timeout 300
 *   ssh <host> cat /tmp/layer_rects.txt
 *
 * Edit the four settings below, then load this file in the CIW.
 * Read-only: opens the cellview in "r" mode and never saves.
 */
LAYER_NAME   = "METAL1"          /* layer to read            */
LAYER_PURPOSE= "drawing"         /* purpose to read          */
TARGET_LIB   = "<lib>"           /* library                  */
TARGET_CELL  = "<cell>"          /* cell                     */
TARGET_VIEW  = "layout"          /* view                     */
OUT_PATH     = "/tmp/layer_rects.txt"
MAX_DEPTH    = 2                 /* hierarchy depth; deeper produces phantom rects */

procedure(LR_EMIT(tag inst xf d out)
  let((m)
    m = inst~>master
    foreach(f m~>shapes
      when(f~>layerName==LAYER_NAME && f~>purpose==LAYER_PURPOSE
        let((tb) tb = dbTransformBBox(f~>bBox xf)
          fprintf(out "RECT %s %.4f %.4f %.4f %.4f\n" tag
                  car(car(tb)) cadr(car(tb)) car(cadr(tb)) cadr(cadr(tb))))))
    when(d < MAX_DEPTH
      foreach(j m~>instances LR_EMIT(tag j dbConcatTransform(xf j~>transform) d+1 out)))
    t))

procedure(LR_RUN()
  let((cv p n)
    cv = dbOpenCellViewByType(TARGET_LIB TARGET_CELL TARGET_VIEW "" "r")
    unless(cv error("cellview not found"))
    p = outfile(OUT_PATH "w")
    fprintf(p "CELL shapes=%d instances=%d layer=%s purpose=%s bbox=%.4f,%.4f,%.4f,%.4f\n"
            length(cv~>shapes) length(cv~>instances) LAYER_NAME LAYER_PURPOSE
            car(car(cv~>bBox)) cadr(car(cv~>bBox)) car(cadr(cv~>bBox)) cadr(cadr(cv~>bBox)))
    n = 0
    foreach(i cv~>instances
      fprintf(p "INST %s %s xy=%.4f,%.4f bbox=%.4f,%.4f,%.4f,%.4f\n" i~>name i~>master~>cellName
              car(i~>xy) cadr(i~>xy) car(car(i~>bBox)) cadr(car(i~>bBox)) car(cadr(i~>bBox)) cadr(cadr(i~>bBox)))
      LR_EMIT(i~>name i i~>transform 0 p)
      n = n + 1)
    foreach(f cv~>shapes
      when(f~>layerName==LAYER_NAME && f~>purpose==LAYER_PURPOSE
        fprintf(p "RECT TOP %.4f %.4f %.4f %.4f\n"
                car(car(f~>bBox)) cadr(car(f~>bBox)) car(cadr(f~>bBox)) cadr(cadr(f~>bBox)))))
    fprintf(p "DONE %d\n" n)
    close(p)
    printf("read_layer: %d instances -> %s\n" n OUT_PATH)
    t))
LR_RUN()
