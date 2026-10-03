"""Headless VTK renderer for trimesh meshes (offscreen, no window)."""
import numpy as np
import vtk
from vtk.util.numpy_support import numpy_to_vtk, numpy_to_vtkIdTypeArray


def _polydata(mesh):
    pts = vtk.vtkPoints()
    pts.SetData(numpy_to_vtk(np.ascontiguousarray(mesh.vertices, dtype=np.float64), deep=True))
    f = np.asarray(mesh.faces, dtype=np.int64)
    cells = np.hstack([np.full((len(f), 1), 3, dtype=np.int64), f]).ravel()
    ca = vtk.vtkCellArray()
    ca.SetCells(len(f), numpy_to_vtkIdTypeArray(cells, deep=True))
    pd = vtk.vtkPolyData()
    pd.SetPoints(pts)
    pd.SetPolys(ca)
    nrm = vtk.vtkPolyDataNormals()
    nrm.SetInputData(pd)
    nrm.SetFeatureAngle(35.0)
    nrm.SplittingOn()
    nrm.ConsistencyOn()
    nrm.AutoOrientNormalsOff()
    nrm.Update()
    return nrm.GetOutput()


class Scene:
    def __init__(self, size=(1600, 1200), bg=(1, 1, 1), bg2=None, ssao=False):
        self.ren = vtk.vtkRenderer()
        self.ren.SetBackground(*bg)
        if bg2 is not None:
            self.ren.GradientBackgroundOn()
            self.ren.SetBackground2(*bg2)
        self.win = vtk.vtkRenderWindow()
        self.win.SetOffScreenRendering(1)
        self.win.AddRenderer(self.ren)
        self.win.SetSize(*size)
        self.win.SetMultiSamples(8)
        self.ren.SetUseFXAA(True)
        self.ren.UseDepthPeelingOn()
        self.ren.SetMaximumNumberOfPeels(8)
        self.win.SetAlphaBitPlanes(1)
        if ssao:
            self.ren.SetUseSSAO(True)
            self.ren.SetSSAORadius(6.0)
            self.ren.SetSSAOKernelSize(64)
        self.actors = []
        self._lights()

    def _lights(self):
        self.ren.RemoveAllLights()
        # camera-space positions: x right, y up, z toward the viewer
        for pos, inten in (((0.6, 1.0, 1.1), 0.80), ((-1.0, 0.4, 0.7), 0.38), ((0.0, 0.6, -1.0), 0.22), ((0.2, -1.0, 0.5), 0.22)):
            l = vtk.vtkLight()
            l.SetLightTypeToCameraLight()
            l.SetPosition(*pos)
            l.SetFocalPoint(0, 0, 0)
            l.SetIntensity(inten)
            self.ren.AddLight(l)

    def add(self, mesh, color, alpha=1.0, specular=0.25, edges=False):
        m = vtk.vtkPolyDataMapper()
        m.SetInputData(_polydata(mesh))
        a = vtk.vtkActor()
        a.SetMapper(m)
        pr = a.GetProperty()
        pr.SetColor(*color)
        pr.SetOpacity(alpha)
        pr.SetSpecular(specular)
        pr.SetSpecularPower(30)
        pr.SetDiffuse(0.85)
        pr.SetAmbient(0.12)
        if edges:
            pr.EdgeVisibilityOn()
            pr.SetEdgeColor(0.2, 0.2, 0.2)
        self.ren.AddActor(a)
        self.actors.append(a)
        return a

    def text(self, s, pos=(20, 20), size=22, color=(0.15, 0.15, 0.15)):
        t = vtk.vtkTextActor()
        t.SetInput(s)
        t.GetTextProperty().SetFontSize(size)
        t.GetTextProperty().SetColor(*color)
        t.GetTextProperty().SetFontFamilyToArial()
        t.SetDisplayPosition(*pos)
        self.ren.AddActor2D(t)

    def camera(self, focal, direction, up=(0, 0, 1), dist=None, parallel=None, view_angle=30.0):
        cam = self.ren.GetActiveCamera()
        d = np.asarray(direction, float)
        d = d / np.linalg.norm(d)
        cam.SetFocalPoint(*focal)
        if dist is None:
            dist = 400.0
        cam.SetPosition(*(np.asarray(focal) + d * dist))
        cam.SetViewUp(*up)
        cam.SetViewAngle(view_angle)
        if parallel is not None:
            cam.ParallelProjectionOn()
            cam.SetParallelScale(parallel)
        self.ren.ResetCameraClippingRange()

    def fit(self, margin=1.05):
        self.ren.ResetCamera()
        cam = self.ren.GetActiveCamera()
        cam.Zoom(1.0 / margin)
        self.ren.ResetCameraClippingRange()

    def image(self):
        self.ren.ResetCameraClippingRange()
        self.win.Render()
        f = vtk.vtkWindowToImageFilter()
        f.SetInput(self.win)
        f.SetInputBufferTypeToRGB()
        f.ReadFrontBufferOff()
        f.Update()
        img = f.GetOutput()
        w, h, _ = img.GetDimensions()
        from vtk.util.numpy_support import vtk_to_numpy
        arr = vtk_to_numpy(img.GetPointData().GetScalars()).reshape(h, w, -1)[::-1]
        return arr[:, :, :3].copy()

    def save(self, path):
        from PIL import Image
        Image.fromarray(self.image()).save(path)

    def clear(self):
        for a in self.actors:
            self.ren.RemoveActor(a)
        self.actors = []
