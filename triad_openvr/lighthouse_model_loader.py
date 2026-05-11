import os
import vtk

_MODULE_DIR = os.path.dirname(os.path.abspath(__file__))

LIGHTHOUSE_MODEL_PATH = os.path.join(
    _MODULE_DIR,
    "lh_basestation_vive",
    "lh_basestation_vive.obj",
)
LIGHTHOUSE_MESH_DECIMATION_RATIO = 0.2

class LighthouseModelLoader:
    def __init__(self, model_path, decimation_ratio=0.5):
        self.model_path = model_path
        self.decimation_ratio = decimation_ratio
        self._cached_polydata = None
        self._cached_face_count = 0

    def prepare_model_polydata(self):
        """Load and cache the Lighthouse model mesh."""
        if self._cached_polydata is not None:
            return self._cached_polydata, self._cached_face_count

        if not os.path.isfile(self.model_path):
            print(f"[LighthouseModelLoader] ✗ Model file not found: {self.model_path}")
            return None, 0

        try:
            reader = vtk.vtkOBJReader()
            reader.SetFileName(self.model_path)
            reader.Update()
            polydata = reader.GetOutput()
            original_faces = polydata.GetNumberOfCells()

            ratio = max(0.01, min(1.0, float(self.decimation_ratio)))
            if ratio < 1.0:
                tri = vtk.vtkTriangleFilter()
                tri.SetInputData(polydata)
                tri.Update()

                decimator = vtk.vtkDecimatePro()
                decimator.SetInputData(tri.GetOutput())
                decimator.SetTargetReduction(1.0 - ratio)
                decimator.SetMaximumError(0.001)
                decimator.SetFeatureAngle(18.0)
                decimator.PreserveTopologyOn()
                decimator.SplittingOn()
                decimator.Update()
                polydata = decimator.GetOutput()

            cached = vtk.vtkPolyData()
            cached.DeepCopy(polydata)
            self._cached_polydata = cached
            self._cached_face_count = cached.GetNumberOfCells()
            print(
                f"[LighthouseModelLoader] ✓ Model cached: {original_faces} -> {self._cached_face_count} faces "
                f"(ratio={ratio:.2f})"
            )
            return self._cached_polydata, self._cached_face_count
        except Exception as e:
            print(f"[LighthouseModelLoader] ✗ Model loading failed: {e}")
            return None, 0

    def create_actor_bundle(self):
        """Create a Lighthouse actor/transform bundle."""
        polydata, _ = self.prepare_model_polydata()
        if polydata is None:
            return None

        mapper = vtk.vtkPolyDataMapper()
        mapper.SetInputData(polydata)

        actor = vtk.vtkActor()
        actor.SetMapper(mapper)
        actor.GetProperty().SetColor(0.5, 0.7, 1.0)
        actor.GetProperty().EdgeVisibilityOff()

        transform = vtk.vtkTransform()
        actor.SetUserTransform(transform)
        return {"actor": actor, "transform": transform}