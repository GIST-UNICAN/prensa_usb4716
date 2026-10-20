import json
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch
from app import App, DEFAULT_CONFIG

class AppTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        with patch.object(App, '_load_config', return_value=json.loads(json.dumps(DEFAULT_CONFIG))):
            self.app=App(demo=True)
        self.app.display_mode.set("Suavizada")
        for key,value in self.app.live_charts.items():value.set(key in ("fd","ft"))
        self.app.plot_interval.set(False)
        self.app.hide_negative.set(False)
        self.app.join_fd.set(False)
        self.app.chart_range.set("Todo")
        self.app.chart_filter.set("Sin filtro")
        self.app.chart_positive.set(False)
        self.app.cfg_path=Path(self.tmp.name)/'config.json'
        self.app.cfg['output_directory']=self.tmp.name
        self.app.update()

    def tearDown(self):
        self.app.dirty=False
        self.app.disconnect()
        self.app.destroy()
        self.tmp.cleanup()

    def test_record_raw_peak_freeze_and_tare(self):
        a=self.app; a.display_mode.set("Directa"); a.connected=True; a.start_recording()
        a._process_sample(1,-1,.5); a._process_sample(2,-2,1)
        self.assertEqual(a.samples[1].vf,-2)
        self.assertAlmostEqual(a.samples[1].force_kp,3941.14)
        a.stop_recording(); peak=a.max_force
        a._process_sample(3,-3,2)
        self.assertEqual(a.max_force,peak)
        a.cfg['tare_samples']=2; a.cfg['force_offset_kp']=20
        a.tare()
        for i in range(302): a._process_sample(4+i*.01,-1,.5)
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
        self.assertEqual(len(a.analysis_ax.lines),4)
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

    def test_pdf_has_uc_logo_on_every_page(self):
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
            self.assertIn('Universidad de Cantabria',page.extract_text())
            self.assertIn('Página',page.extract_text())
            self.assertGreaterEqual(len(page.images),1)
        self.assertIn('SIMULACIÓN',report.pages[0].extract_text())
        a.cfg['logo_path']=str(root/'missing.png')
        with self.assertRaises(ValueError):
            a._build_pdf(str(root/'missing.pdf'),root/'fd.png',root/'ft.png')


    def test_smoothing_preserves_raw_samples(self):
        a=self.app; a.connected=True; a.start_recording()
        a._process_sample(10, -1, .2)
        a._process_sample(10.5, -3, .4)
        self.assertEqual(a.current_force.get(), "0")
        a._process_sample(11, -2, .3)
        a._redraw_plots()
        self.assertAlmostEqual(float(a.current_force.get()), 4926)
        self.assertEqual([s.vf for s in a.samples], [-1, -3, -2])
        a.display_mode.set("Directa"); a._reset_display()
        a._process_sample(11.1, -1, .2)
        a._redraw_plots()
        self.assertAlmostEqual(float(a.current_force.get()), 1971)
        a._refresh_debug()
        self.assertIn("-1.000000", a.debug_values.get())

    def test_indicators_keep_geometry(self):
        a=self.app
        a.geometry("1050x700"); a.update()
        values=[a.current_force, a.current_kn, a.current_def, a.max_force_var, a.max_def_var]
        boxes = next(child for child in a.tab_test.winfo_children() if child.winfo_children() and all(type(box).__name__=='Labelframe' for box in child.winfo_children())).winfo_children()
        geometry = [(box.winfo_x(), box.winfo_width()) for box in boxes]
        for value in values: value.set("-12345678.123")
        a.update()
        self.assertEqual(geometry, [(box.winfo_x(), box.winfo_width()) for box in boxes])
        for left, right in zip(boxes, boxes[1:]):
            self.assertLessEqual(left.winfo_x()+left.winfo_width(), right.winfo_x())
        for value in values: value.set("0")
        a.update()
        self.assertGreater(a.tab_test.winfo_width(), 1000)

    def test_noise_capture_export_and_cancel(self):
        a=self.app; a.connected=True
        a.start_noise_capture()
        for i in range(101): a._process_sample(20+i/10, -.1, .02)
        self.assertIsNone(a.noise_capture)
        self.assertEqual(a.noise_result['samples'],101)
        self.assertEqual(len(a.samples),0)
        self.assertIn('SIMULACIÓN',a.noise_status.get())
        path=Path(self.tmp.name)/'noise.csv'
        with patch('app.filedialog.asksaveasfilename', return_value=str(path)): a.save_noise_capture()
        meta=json.loads(path.with_suffix('.metadata.json').read_text(encoding='utf-8'))
        self.assertTrue(meta['demo'])
        self.assertEqual(meta['summary']['samples'],101)
        a.start_noise_capture(); a._process_sample(40,0,0); a.tare()
        self.assertIsNone(a.noise_capture)
        self.assertIsNone(a.noise_result)

    def test_kalman_keeps_raw_samples_peaks_and_debug(self):
        a=self.app; a.connected=True; a.start_recording()
        a.display_mode.set("Kalman"); a._reset_display()
        for i in range(101): a._process_sample(10+i*.01, -1 if i%2 else -2, .2)
        self.assertEqual(a.samples[-1].vf,-2)
        self.assertAlmostEqual(a.max_force,3941.14)
        a._redraw_plots()
        self.assertGreater(float(a.current_force.get()),1970.57)
        self.assertLess(float(a.current_force.get()),3941.14)
        self.assertEqual(a.debug_history[-1][1],-2)
        self.assertNotEqual(a.filtered_history[-1][1],-2)
        a._refresh_debug()
        self.assertEqual(len(a.debug_ax.lines),4)
        a.display_mode.set("Directa"); a._reset_display()
        self.assertEqual(len(a.filtered_history),0)
        a._process_sample(12,-3,.4)
        a._redraw_plots()
        self.assertAlmostEqual(float(a.current_force.get()),5912)

    def _feed_training(self):
        import random
        rng=random.Random(123)
        self.app.connected=True
        self.app.training_seconds.set('10')
        self.app.start_kalman_training()
        for i in range(1001):
            self.app._capture_noise_sample(i/100,.2+rng.gauss(0,.01),.01+rng.gauss(0,.002))

    def test_training_persistence_and_panel(self):
        a=self.app
        self.assertFalse(a.kalman_panel.winfo_manager())
        a.toggle_kalman_panel()
        self.assertEqual(a.kalman_panel.winfo_manager(),'pack')
        self._feed_training()
        self.assertEqual(a.display_mode.get(),'Kalman')
        self.assertTrue(a._kalman_profile_path().exists())
        expected=a.voltage_filters[0].r
        a._load_kalman_profile()
        self.assertEqual(a.voltage_filters[0].r,expected)
        a.toggle_kalman_panel()
        self.assertFalse(a.kalman_panel.winfo_manager())
        self.assertEqual(a.display_mode.get(),'Kalman')
        a.cfg['force_channel']=4; a._load_kalman_profile()
        self.assertIsNone(a.kalman_profile)
        a.demo=False; a._load_kalman_profile()
        self.assertIsNone(a.kalman_profile)
        self.assertFalse(a._kalman_profile_path().exists())

    def test_failed_training_keeps_previous_filter(self):
        a=self.app; self._feed_training()
        previous=a.kalman_profile
        old=a._kalman_profile_path().read_text(encoding='utf-8')
        a.start_kalman_training()
        for i in range(1001): a._capture_noise_sample(20+i/100,i/100*.1,0)
        self.assertIs(a.kalman_profile,previous)
        self.assertEqual(a._kalman_profile_path().read_text(encoding='utf-8'),old)
        self.assertIn('no aplicado',a.noise_status.get())
        a.start_kalman_training(); a.cancel_noise_capture()
        self.assertIs(a.kalman_profile,previous)
        with patch('app.Path.replace',side_effect=OSError('sin permiso')):
            self._feed_training()
        self.assertIs(a.kalman_profile,previous)
        self.assertEqual(a._kalman_profile_path().read_text(encoding='utf-8'),old)

    def test_debug_curves_toggle_independently_of_display(self):
        a=self.app; a.display_mode.set('Directa')
        a._process_sample(0,.1,.2); a._process_sample(.01,.2,.1)
        a._refresh_debug()
        self.assertEqual(len(a.debug_ax.lines),4)
        a.debug_visible['raw_force'].set(False); a._refresh_debug()
        self.assertEqual(len(a.debug_ax.lines),3)
        self.assertNotIn('Fuerza original',[line.get_label() for line in a.debug_ax.lines])
        for v in a.debug_visible.values(): v.set(False)
        a._refresh_debug(); self.assertEqual(len(a.debug_ax.lines),0)
        a.debug_visible['filtered_force'].set(True); a._refresh_debug()
        self.assertEqual(len(a.debug_ax.lines),1)
        self.assertIn('corregida',a.debug_ax.lines[0].get_label())
        self.assertEqual(a.display_mode.get(),'Directa')

    def test_large_negative_oscillation_warns_without_clipping(self):
        a=self.app; a.connected=True; a.start_recording()
        for i in range(101): a._process_sample(10+i*.01, .1, -4 if i%2 else 0)
        self.assertIn('oscilación',a.status.get())
        self.assertEqual(min(s.vd for s in a.samples),-4)
        a._refresh_debug()
        self.assertIn('Deformación: saltos repetidos',a.debug_values.get())

    def test_debug_layout_preserves_graph_space(self):
        a=self.app; a.geometry('1050x700'); a.nb.select(a.tab_config);a.config_notebook.select(a.tab_debug)
        a._process_sample(0,.1,-.1); a._refresh_debug(); a.update()
        self.assertFalse(hasattr(a,'noise_text'))
        canvas=a.debug_canvas.get_tk_widget()
        closed=canvas.winfo_height()
        self.assertGreaterEqual(closed,350)
        a.toggle_kalman_panel(); a.toggle_connection_panel(); a.update()
        self.assertGreaterEqual(canvas.winfo_height(),240)
        self.assertLessEqual(canvas.winfo_rooty()+canvas.winfo_height(),a.winfo_rooty()+a.winfo_height())
        a.toggle_kalman_panel(); a.toggle_connection_panel(); a.update()
        self.assertEqual(canvas.winfo_height(),closed)

    def test_global_kalman_strength_and_plot_preserve_originals(self):
        a=self.app; a.connected=True; a.start_recording()
        for i in range(101): a._process_sample(10+i*.01, -1 if i%2 else -2, .2)
        original=[s.force_kp for s in a.samples]
        a.display_mode.set('Kalman'); a.kalman_strength.set('Normal'); a._display_controls_changed()
        q=a.voltage_filters[0].q_per_second
        a.kalman_strength.set('Muy alto'); a._display_controls_changed()
        self.assertAlmostEqual(a.voltage_filters[0].q_per_second,q*.01)
        self.assertEqual(a.ax_ft.get_title(),'Fuerza · tiempo')
        self.assertNotEqual(list(a.ax_ft.lines[0].get_ydata()),original)
        self.assertEqual([s.force_kp for s in a.samples],original)
        a.display_mode.set('Directa'); a._display_controls_changed()
        self.assertEqual(list(a.ax_ft.lines[0].get_ydata()),original)

    def _ring_point(self, vf, vd, at_one):
        a=self.app; now=time.perf_counter()
        a.recent_volts=[(now-.24+i*.01, vf+(-1)**i*.0001, vd+(-1)**i*.0001) for i in range(25)]
        a.capture_ring_point(at_one)

    def test_ring_calibration_saves_both_channels(self):
        a=self.app; a.connected=True; a.ring_channels.set('Ambas')
        self._ring_point(.1,.2,False)
        self._ring_point(-.9,.6,True)
        z=dict(a.ring_zero); o=dict(a.ring_one)
        a.ring_force.set('2000'); a.save_ring_calibration()
        cfg=json.loads(a.cfg_path.read_text(encoding='utf-8'))
        for factor,offset,key,target in [('force_factor_kp_per_v','force_offset_kp','vf',2000),
                                         ('deformation_factor_mm_per_v','deformation_offset_mm','vd',1)]:
            self.assertAlmostEqual(cfg[factor]*z[key]+cfg[offset],0)
            self.assertAlmostEqual(cfg[factor]*o[key]+cfg[offset],target)
        self.assertEqual(cfg['calibration_history'][-1]['method'],'ring_zero_and_1mm')
        self.assertIsNone(a.ring_one)
        self.assertEqual(a.zero_force_v,0)

    def test_ring_rejects_missing_reference_and_no_voltage_span(self):
        a=self.app; a.connected=True
        self._ring_point(.1,.2,False); self._ring_point(.1,.2,True)
        original=json.dumps(a.cfg)
        with patch('workbench.messagebox.showerror') as error:
            a.save_ring_calibration()
            a.ring_force.set('2000'); a.save_ring_calibration()
        self.assertEqual(error.call_count,2)
        self.assertEqual(json.dumps(a.cfg),original)
        self.assertFalse(a.cfg_path.exists())

    def test_interval_crops_view_without_deleting_samples(self):
        from app import Sample
        a=self.app
        a.samples=[Sample(i/100,0,0,max(0,100*(1-abs(i/100-2.5)/1.5)),0) for i in range(601)]
        a.plot_interval.set(True); a._redraw_plots()
        times=list(a.ax_ft.lines[0].get_xdata())
        self.assertGreater(times[0],.9); self.assertLess(times[-1],4.3)
        self.assertEqual(len(a.samples),601)
        self.assertIn('Final',a.interval_status.get())
        a.plot_interval.set(False); a._redraw_plots()
        self.assertEqual(len(a.ax_ft.lines[0].get_xdata()),601)

    def test_live_chart_selection_and_negative_view(self):
        import math
        a=self.app; a.connected=True; a.start_recording(); a.display_mode.set('Directa')
        a._process_sample(1,-1,-.1); a._process_sample(2,-2,.2)
        a.hide_negative.set(True); a._redraw_plots()
        self.assertEqual(a.ax_fd.lines[0].get_xdata()[0],0)
        self.assertEqual(a.ax_fd.lines[0].get_linestyle(),'None')
        self.assertLess(a.samples[0].deformation_mm,0)
        for v in a.live_charts.values(): v.set(True)
        a._redraw_plots(); self.assertEqual(len(a.fig.axes),5)
        for k,v in a.live_charts.items(): v.set(k=='volts')
        a._redraw_plots(); self.assertEqual(len(a.fig.axes),1)
        self.assertEqual(len(a.fig.axes[0].lines),2)
        for v in a.live_charts.values(): v.set(False)
        a._redraw_plots(); self.assertEqual(len(a.fig.axes),0)

    def test_ring_failed_save_is_atomic(self):
        a=self.app; a.connected=True
        self._ring_point(.1,.2,False); self._ring_point(-.9,.6,True); a.ring_force.set('2000')
        before=json.dumps(a.cfg)
        with patch('workbench.Path.replace',side_effect=OSError('sin permiso')), patch('workbench.messagebox.showerror') as error:
            a.save_ring_calibration()
        error.assert_called_once()
        self.assertEqual(json.dumps(a.cfg),before)
        self.assertFalse(a.cfg_path.exists())
        self.assertIsNotNone(a.ring_one)

    def test_ring_deformation_preserves_force_and_reloads(self):
        a=self.app; a.connected=True; a.zero_force_v=.123
        old=(a.cfg['force_factor_kp_per_v'],a.cfg['force_offset_kp'])
        self._ring_point(.1,.2,False); self._ring_point(.1,.6,True)
        zero=a.ring_zero['vd']; one=a.ring_one['vd']
        a.save_ring_calibration()
        loaded=a._load_config()
        self.assertEqual((loaded['force_factor_kp_per_v'],loaded['force_offset_kp']),old)
        self.assertEqual(a.zero_force_v,.123)
        self.assertAlmostEqual(loaded['deformation_factor_mm_per_v']*zero+loaded['deformation_offset_mm'],0)
        self.assertAlmostEqual(loaded['deformation_factor_mm_per_v']*one+loaded['deformation_offset_mm'],1)
        self.assertIn(str(a.cfg_path.resolve()),a.active_calibration.get())

    def test_select_saved_deformation_preserves_force(self):
        a=self.app
        original=a.cfg['force_factor_kp_per_v']
        a.cal_versions['Prueba']={**a.cfg,'deformation_factor_mm_per_v':1.25,'deformation_offset_mm':2.}
        a.cal_version.set('Prueba'); a.cal_channel.set('Deformación (mm)')
        a.preview_calibration_version()
        self.assertIn('diferencia',a.cal_comparison.get())
        a.apply_calibration_version()
        self.assertEqual(a.cfg['force_factor_kp_per_v'],original)
        self.assertEqual(a._load_config()['deformation_factor_mm_per_v'],1.25)

    def test_plot_removes_spike_without_changing_record(self):
        from app import Sample
        a=self.app; a.display_mode.set('Directa')
        a.samples=[Sample(i/100,1,1,100,1) for i in range(21)]
        a.samples[10]=Sample(.1,1,1,9000,1)
        self.assertEqual(a._visible_plot_samples()[10].force_kp,100)
        self.assertEqual(a.samples[10].force_kp,9000)

    def test_rupture_banner_red_curve_and_archive(self):
        from app import Sample
        a=self.app; a.connected=True; a.start_recording()
        a.samples=[Sample(i/100,0,0,0 if i<100 else max(0,min(100,(i-100)/2,(700-i)/2)),i/100) for i in range(801)]
        a.stop_recording()
        self.assertIn('PROBETA ROTA',a.rupture_status.get())
        self.assertIn('desde inicio detectado',a.rupture_status.get())
        self.assertIn('mm',a.rupture_status.get())
        self.assertIn('Estabilidad S corregida',a.marshall_text.get())
        self.assertTrue(any(line.get_color()=='#c62828' for line in a.ax_ft.lines))
        self.assertIsNotNone(a.test_context['rupture_estimate'])
        a._save_plot_file(Path(self.tmp.name)/'rotura.png','ft')
        self.assertTrue((Path(self.tmp.name)/'rotura.png').exists())

    def test_live_rupture_turns_red_within_one_second(self):
        from app import Sample
        a=self.app;a.connected=True;a.display_mode.set('Media de 10 lecturas');a.start_recording()
        rows=[Sample(i/100,0,0,0 if i<100 else min(1000,(i-100)*5),i/100) for i in range(401)]
        rows += [Sample(i/100,0,0,1000-30*(i/100-4),i/100) for i in range(401,476)]
        a.samples=rows[:421];a._redraw_plots()
        self.assertNotIn('PROBETA ROTA',a.rupture_status.get())
        a.samples=rows;a._redraw_plots()
        self.assertTrue(a.recording)
        self.assertIn('PROBETA ROTA',a.rupture_status.get())
        self.assertTrue(any(line.get_color()=='#c62828' for line in a.ax_ft.lines))

    def test_calibration_only_inside_configuration(self):
        a=self.app
        self.assertFalse(any('laboratorio' in a.nb.tab(t,'text').lower() for t in a.nb.tabs()))
        self.assertTrue(str(a.calibration_laboratory).startswith(str(a.tab_config)+'.'))
        self.assertEqual(len(a.calibration_notebook.tabs()),2)

    def test_legacy_display_block_and_tare(self):
        a=self.app; a.connected=True; a.display_mode.set('Antiguo (10 lecturas)')
        a.tare()
        for i in range(99): a._process_sample(i*.01,.2,.3)
        self.assertTrue(a.tare_pending)
        a._process_sample(.99,.2,.3)
        self.assertFalse(a.tare_pending)
        self.assertEqual(float(a.current_force.get()),0)
        for i in range(9): a._process_sample(1+i*.01,.1,.4)
        self.assertEqual(float(a.current_force.get()),0)
        a._process_sample(1.09,.1,.4)
        self.assertAlmostEqual(float(a.current_force.get()),197,places=0)

    def test_legacy_graph_equals_txt_points(self):
        from app import Sample
        from legacy_processing import legacy_text
        a=self.app; a.display_mode.set('Antiguo (10 lecturas)'); a.join_fd.set(True)
        a.samples=[Sample(i/100,-1,1,100,2) for i in range(40)]
        visible=a._visible_plot_samples()
        lines=legacy_text([vars(r) for r in a.samples]).splitlines()
        self.assertEqual(len(visible),len(lines))
        for r,line in zip(visible,lines):
            d,f,t=map(float,line.split('*'))
            self.assertAlmostEqual(r.deformation_mm,d/100)
            self.assertEqual(r.force_kp,f)
        a._redraw_plots()
        self.assertEqual(a.ax_fd.lines[0].get_linestyle(),'-')

    def test_median_live_display_matches_curve(self):
        a=self.app; a.connected=True; a.start_recording(); a.display_mode.set('Mediana')
        for i in range(30): a._process_sample(1+i*.01,-.01*i,.01*i if i!=20 else -.5)
        a._redraw_plots()
        visible=a._visible_plot_samples()
        self.assertAlmostEqual(float(a.current_def.get()),visible[-1].deformation_mm,places=2)
        self.assertAlmostEqual(float(a.current_force.get()),round(visible[-1].force_kp),places=0)
        self.assertTrue(all(y.deformation_mm>=x.deformation_mm for x,y in zip(visible,visible[1:])))

    def test_kalman_zero_option_uses_tare_and_preserves_raw(self):
        a=self.app; a.connected=True
        a.stable_zero.set(True); a._stable_zero_changed()
        self.assertEqual(a.display_mode.get(),'Kalman')
        self.assertIsNone(a.zero_holds)
        a.tare()
        for i in range(100): a._process_sample(i*.01,.2+(-1)**i*.001,.3+(-1)**i*.001)
        a.start_recording()
        for i in range(100): a._process_sample(2+i*.01,.2+(-1)**i*.001,.3+(-1)**i*.001)
        a._redraw_plots()
        self.assertEqual(float(a.current_force.get()),0)
        self.assertEqual(float(a.current_def.get()),0)
        self.assertTrue(any(s.force_kp!=0 for s in a.samples))
        self.assertTrue(a.test_context['stable_zero']['enabled'])

    def test_window_units_and_negative_exclusion(self):
        a=self.app; a.connected=True; a.start_recording(); a.display_mode.set('Suavizada')
        a._process_sample(1,-1,.1); a._process_sample(1.1,1,.2); a._process_sample(1.2,-2,.3)
        a._redraw_plots()
        self.assertEqual(a.current_force.get(),'2956')
        self.assertEqual(a.current_kn.get(),'29.0')
        self.assertLess(a.samples[1].force_kp,0)
        self.assertAlmostEqual(a.processed_current.force_kp,2955.855)

    def test_results_layout_fits_minimum_window(self):
        a=self.app;a.geometry('1050x700');a.nb.select(a.tab_data);a.update()
        canvas=a.marshall_canvas.get_tk_widget()
        self.assertGreater(canvas.winfo_height(),180)
        cards=a.marshall_cards
        last=cards.winfo_children()[-1]
        self.assertLessEqual(last.winfo_rooty()+last.winfo_height(),canvas.winfo_rooty()+canvas.winfo_height())

    def test_three_tabs_and_operator_controls(self):
        a=self.app
        self.assertEqual([a.nb.tab(t,'text') for t in a.nb.tabs()],['Directo','Exportar','Configuración'])
        a.nb.select(a.tab_test);a.update()
        def buttons(widget):
            result=[]
            for child in widget.winfo_children():
                if child.winfo_class()=='TButton' and child.winfo_viewable():result.append(child.cget('text'))
                result+=buttons(child)
            return result
        self.assertEqual(buttons(a.tab_test).count('Iniciar ensayo'),1)
        self.assertIn('Conectar',buttons(a.tab_test))
        self.assertIn('Guardar nombre',buttons(a.tab_test))
        self.assertIn('Tarar',buttons(a.tab_test))
        self.assertIn('Reiniciar',buttons(a.tab_test))
        a.nb.select(a.tab_data);a.update()
        self.assertIn('Exportar Excel',buttons(a.tab_data))
        self.assertNotIn('CSV',buttons(a.tab_data))
        a.extra_exports.set(True);a._update_extra_exports();a.update()
        self.assertIn('CSV',buttons(a.tab_data))

    def test_operator_start_tares_and_preserves_view_preferences_zero(self):
        a=self.app;a.connected=True
        a.operator_trial_action()
        self.assertTrue(a.tare_pending)
        for i in range(100):a._process_sample(i*.01,.2,.3)
        a.update()
        self.assertTrue(a.recording)
        self.assertEqual(a.btn_start.cget('text'),'Finalizar ensayo')
        a.operator_trial_action()
        self.assertFalse(a.recording)
        zero=a.zero_force_v
        a.save_view_preferences()
        self.assertEqual(a.zero_force_v,zero)
        self.assertEqual(json.loads(a.cfg_path.read_text())['view_settings']['mode'],a.display_mode.get())

    def test_history_marks_latest_and_loads_export_without_resampling(self):
        a=self.app;a.connected=True;a.start_recording()
        for i in range(25):a._process_sample(1+i*.01,-i*.01,i*.01)
        a.stop_recording();identifier=a.session_id
        self.assertEqual(a.history_tree.item(identifier,'values')[0],'Último')
        a.history_tree.selection_set(identifier);a.open_history()
        self.assertEqual(a.nb.select(),str(a.tab_data))
        processed=a.current_export_session()
        self.assertEqual(len(processed['samples']),3)
        from marshall_results import session_results
        self.assertEqual(len(session_results(processed)['rows']),3)
        self.assertEqual(session_results(processed)['rows'][-1]['samples_count'],5)

    def test_mean_ten_geometry_and_delete_loaded_history(self):
        a=self.app;a.connected=True;a.display_mode.set('Media de 10 lecturas')
        a.specimen_height.set('63,5');a.specimen_volume.set('500000')
        a.start_recording()
        for i in range(20):a._process_sample(1+i*.01,-i*.01,i*.01)
        visible=a._visible_plot_samples()
        self.assertEqual(len(visible),2)
        self.assertAlmostEqual(visible[0].force_kp,4.5*.01*1970.57)
        a.stop_recording();identifier=a.session_id
        stored=a.session_store().get(identifier)
        self.assertEqual(stored['configuration']['specimen_height_mm'],63.5)
        a.specimen_height.set('');a.restore_session(stored,archived=True)
        self.assertEqual(a.specimen_height.get(),'63.5')
        self.assertEqual(a.current_export_session()['configuration']['specimen_volume_mm3'],500000)
        self.assertTrue(a.delete_history_session(identifier))
        self.assertEqual(a.session_store().list(),[])
        self.assertEqual(a.samples,[])
        self.assertIsNone(a.session_id)

    def test_geometry_validation_and_manual_tare_reused(self):
        a=self.app;a.connected=True;a.specimen_height.set('-1')
        with patch('app.messagebox.showerror') as error:a.start_recording()
        error.assert_called_once();self.assertFalse(a.recording)
        a.specimen_height.set('');a.operator_tare()
        for i in range(100):a._process_sample(i*.01,.2,.3)
        self.assertTrue(a.tare_valid)
        a.operator_trial_action();self.assertTrue(a.recording)
        self.assertFalse(a.tare_pending)

    def test_save_name_before_and_after_archiving(self):
        a=self.app;a.test_name.set('Probeta norte');a.save_trial_name()
        self.assertEqual(json.loads(a.cfg_path.read_text())['draft_trial_reference'],'Probeta norte')
        self.assertEqual(a.name_saved.get(),'Nombre guardado')
        a.connected=True;a.start_recording();a._process_sample(1,-1,.2);a.stop_recording()
        identifier=a.session_id;a.test_name.set('Probeta norte revisada');a.save_trial_name()
        self.assertEqual(a.session_store().get(identifier)['metadata']['reference'],'Probeta norte revisada')
        self.assertEqual(len(a.session_store().list()),1)

    def test_automatic_connection_failure_is_non_modal(self):
        a=self.app
        with patch('app.MockDAQ') as daq,patch('app.messagebox.showerror') as error:
            daq.return_value.connect.side_effect=RuntimeError('USB ausente')
            a.connect(automatic=True)
            error.assert_not_called()
        self.assertFalse(a.connected)
        self.assertIn('no disponible',a.connection_state.get())
        a.nb.select(a.tab_test);a.update()
        self.assertTrue(a.btn_connect.winfo_viewable())

if __name__=='__main__':unittest.main()
