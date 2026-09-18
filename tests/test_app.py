import json
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch
from app import App

class AppTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.app=App(demo=True)
        self.app.cfg_path=Path(self.tmp.name)/'config.json'
        self.app.cfg['output_directory']=self.tmp.name
        self.app.update()

    def tearDown(self):
        self.app.dirty=False
        self.app.disconnect()
        self.app.destroy()
        self.tmp.cleanup()

    def test_record_raw_peak_freeze_and_tare(self):
        a=self.app; a.connected=True; a.start_recording()
        a._process_sample(1,-1,.5); a._process_sample(2,-2,1)
        self.assertEqual(a.samples[1].vf,-2)
        self.assertAlmostEqual(a.samples[1].force_kp,3941.14)
        a.stop_recording(); peak=a.max_force
        a._process_sample(3,-3,2)
        self.assertEqual(a.max_force,peak)
        a.cfg['tare_samples']=2; a.cfg['force_offset_kp']=20
        a.tare(); a._process_sample(4,-1,.5); a._process_sample(5,-1,.5); a._process_sample(6,-1,.5)
        self.assertAlmostEqual(float(a.current_force.get()),0)

    def test_calibration_csv_roundtrip(self):
        a=self.app
        a.cal_points=[(0,10),(-1,2010),(-2,4010)]
        a.refresh_calibration(); a.apply_calibration()
        self.assertEqual(a.cfg['force_factor_kp_per_v'],-2000)
        self.assertEqual(len(json.loads(a.cfg_path.read_text())['calibration_history']),1)
        a.connected=True; a.start_recording(); a._process_sample(1,-1,.5); a.stop_recording()
        path=str(Path(self.tmp.name)/'test.csv')
        with patch('app.filedialog.asksaveasfilename',return_value=path):a.save_csv()
        self.assertFalse(a.dirty)
        with patch('workbench.filedialog.askopenfilename',return_value=path):a.open_test()
        self.assertEqual(a.samples[0].force_kp,2010)
        self.assertEqual(a.test_context['force_factor_kp_per_v'],-2000)

    def test_rejected_config_is_atomic(self):
        a=self.app; original=json.dumps(a.cfg)
        a.cfg_vars['sample_hz'].set('-10')
        with patch('app.messagebox.showerror') as error:a.save_configuration()
        error.assert_called_once()
        self.assertEqual(json.dumps(a.cfg),original)
        self.assertFalse(a.cfg_path.exists())

    def test_demo_thread_disconnect(self):
        a=self.app; a.connect(); a.start_recording()
        a.after(1500, a.quit)
        a.mainloop()
        a.stop_recording(); a.disconnect()
        self.assertGreater(len(a.samples),10)
        self.assertFalse(a.worker.is_alive())
        self.assertTrue(a.q.empty())

    def test_archive_restore_compare_and_metadata_update(self):
        a=self.app; a.connected=True
        a.test_name.set('Primero'); a.start_recording()
        a._process_sample(1,-1,.5); a._process_sample(2,-2,1); a.stop_recording()
        first=a.session_id
        self.assertFalse(a.dirty)
        self.assertEqual(len(a.session_store().list()),1)
        a.notes.set('Observación revisada'); self.assertTrue(a.dirty)
        a.archive_current(); self.assertEqual(len(a.session_store().list()),1)
        a.start_recording(); a.test_name.set('Segundo')
        a._process_sample(3,-1,.4); a._process_sample(4,-3,1.2); a.stop_recording()
        second=a.session_id; self.assertNotEqual(first,second)
        a.history_tree.selection_set([first,second]); a.compare_history()
        self.assertEqual(len(a.comparisons),2)
        self.assertEqual(len(a.analysis_ax.lines),2)
        a.history_tree.selection_set(first); a.open_history()
        self.assertEqual(a.test_name.get(),'Primero')
        self.assertEqual(a.notes.get(),'Observación revisada')
        self.assertEqual(a.samples[-1].vf,-2)
        self.assertFalse(a.dirty)
        self.assertEqual(a.comparisons,[])
        path=str(Path(self.tmp.name)/'batch.zip')
        a.history_tree.selection_set([first,second])
        with patch('analysis_ui.filedialog.asksaveasfilename',return_value=path): a.export_history_batch()
        import zipfile
        with zipfile.ZipFile(path) as archive:
            self.assertEqual(len([name for name in archive.namelist() if name.endswith('/ensayo.json')]),2)

    def test_archive_failure_keeps_data_unsaved(self):
        a=self.app; a.connected=True; a.start_recording(); a._process_sample(1,-1,.5)
        with patch('sessions.SessionStore.save',side_effect=OSError('sin espacio')), patch('analysis_ui.messagebox.showerror') as error:
            a.stop_recording()
        self.assertTrue(a.dirty); self.assertEqual(len(a.samples),1)
        error.assert_called_once()

    def test_pdf_has_uca_logo_on_every_page(self):
        try:
            from pypdf import PdfReader
        except ImportError:
            self.skipTest('pypdf necesario para inspeccionar PDF')
        a=self.app; a.connected=True; a.start_recording()
        for i in range(12): a._process_sample(i+1,-i*.1,i*.05)
        a.stop_recording()
        root=Path(self.tmp.name)
        a._save_plot_file(root/'fd.png','fd'); a._save_plot_file(root/'ft.png','ft')
        a._build_pdf(str(root/'report.pdf'),root/'fd.png',root/'ft.png')
        report=PdfReader(root/'report.pdf')
        self.assertGreaterEqual(len(report.pages),3)
        for page in report.pages:
            self.assertIn('Universidad de Cádiz',page.extract_text())
            self.assertIn('Página',page.extract_text())
            self.assertGreaterEqual(len(page.images),1)
        self.assertIn('SIMULACIÓN',report.pages[0].extract_text())
        a.cfg['logo_path']=str(root/'missing.png')
        with self.assertRaises(ValueError):
            a._build_pdf(str(root/'missing.pdf'),root/'fd.png',root/'ft.png')

if __name__=='__main__':unittest.main()
