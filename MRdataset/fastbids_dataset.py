import logging
from pathlib import Path

from MRdataset.base import Project, Run, Modality, Subject, Session
from MRdataset.utils import select_parameters, get_ext, files_under_folder

# Module-level logger
logger = logging.getLogger('root')


# TODO: check what if each variable is None. Apply try catch
class FastBIDSDataset(Project):
    """

    """

    def __init__(self,
                 name='mind',
                 data_root=None,
                 metadata_root=None,
                 include_phantom=False,
                 reindex=False,
                 include_nifti_header=False,
                 **kwargs):

        """
        Parameters
        ----------
        name : str
            an identifier/name for the dataset
        data_root : Path or str
            directory containing dicom files, supports nested hierarchies
        metadata_root : str or Path
            directory to store cache
        include_phantom : bool
            whether to include localizer/aahead_scout/phantom/acr
        reindex : bool
            If true, rejects stored cache and rebuilds index
        include_nifti_header :
            whether to check nifti headers for compliance,
            only used when --style==bids
        Examples
        --------
        >>> from MRdataset.fastbids_dataset import FastBIDSDataset
        >>> dataset = FastBIDSDataset()
        """

        super().__init__(name, data_root, metadata_root)

        self.include_phantom = include_phantom
        self.include_nifti_header = include_nifti_header
        indexed = self.cache_path.exists()
        if not indexed or reindex:
            self.walk()
            self.save_dataset()
        else:
            self.load_dataset()

    def walk(self):
        # TODO: Need to handle BIDS datasets without JSON files
        for file in files_under_folder(self.data_root, '.json'):
            datatype = file.parent.name
            modality_obj = self.get_modality(datatype)
            if modality_obj is None:
                modality_obj = Modality(datatype)
            nSub = file.parents[2].name
            subject_obj = modality_obj.get_subject(nSub)
            if subject_obj is None:
                subject_obj = Subject(nSub)
            nSess = file.parents[1].name
            session_node = subject_obj.get_session(nSess)
            if session_node is None:
                session_node = Session(nSess)
                session_node = self.parse(session_node,
                                          file)
                if session_node.runs:
                    subject_obj.add_session(session_node)
                if subject_obj.sessions:
                    modality_obj.add_subject(subject_obj)
            if modality_obj.subjects:
                self.add_modality(modality_obj)
        if not self.modalities:
            raise EOFError("Expected Sidecar JSON files in --data_root. Got 0")

    def parse(self, session_node, filepath):
        # files = bids_layout.get(**filters)
        # for file in files:
        filename = filepath.name
        ext = filepath.suffix
        if ext == '.json':
            parameters = select_parameters(filepath, ext)
        elif ext in ['.nii', '.nii.gz']:
            parameters = select_parameters(filepath, ext)
        else:
            raise NotImplementedError(f"Got {ext}, Expects .nii/.json")
        if parameters:
            run_node = session_node.get_run(filename)
            if run_node is None:
                run_node = Run(filename)
            for k, v in parameters.items():
                run_node.params[k] = v
            run_node.echo_time = round(parameters.get('EchoTime', 1.0), 4)
            session_node.add_run(run_node)
        return session_node
