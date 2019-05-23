#!/usr/bin/env python
# -*- coding: utf-8 -*-

#############################################################################
#  Copyright Kitware Inc.
#
#  Licensed under the Apache License, Version 2.0 ( the "License" );
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
#############################################################################

import json
import os
import six
import time

from girder import config, events
from girder.exceptions import ValidationException
from girder.models.item import Item
from girder.models.setting import Setting
from tests import base

from . import common


# boiler plate to start and stop the server

os.environ['GIRDER_PORT'] = os.environ.get('GIRDER_TEST_PORT', '20200')
config.loadConfig()  # Must reload config to pickup correct port


def setUpModule():
    base.enabledPlugins.append('large_image')
    base.startServer(False)


def tearDownModule():
    base.stopServer()


# Test large_image endpoints
class LargeImageLargeImageTest(common.LargeImageCommonTest):
    def _waitForJobToBeRunning(self, job):
        from girder.plugins.jobs.constants import JobStatus
        from girder.plugins.jobs.models.job import Job
        job = Job().load(id=job['_id'], force=True)
        while job['status'] != JobStatus.RUNNING:
            time.sleep(0.01)
            job = Job().load(id=job['_id'], force=True)
        return job

    def _createThumbnails(self, spec, cancel=False):
        from girder.plugins.jobs.constants import JobStatus
        from girder.plugins.jobs.models.job import Job

        params = {'spec': json.dumps(spec)}
        if cancel:
            params['logInterval'] = 0
        resp = self.request(
            method='PUT', path='/large_image/thumbnails', user=self.admin,
            params=params)
        self.assertStatusOk(resp)
        job = resp.json
        if cancel:
            job = self._waitForJobToBeRunning(job)
            job = Job().cancelJob(job)

        starttime = time.time()
        while True:
            self.assertTrue(time.time() - starttime < 30)
            resp = self.request('/job/%s' % str(job['_id']))
            self.assertStatusOk(resp)
            if resp.json.get('status') == JobStatus.SUCCESS:
                return True
            if resp.json.get('status') == JobStatus.ERROR:
                return False
            if resp.json.get('status') == JobStatus.CANCELED:
                return 'canceled'
            time.sleep(0.1)

    def testSettings(self):
        from girder.plugins.large_image import constants

        for key in (constants.PluginSettings.LARGE_IMAGE_SHOW_THUMBNAILS,
                    constants.PluginSettings.LARGE_IMAGE_SHOW_VIEWER,
                    constants.PluginSettings.LARGE_IMAGE_AUTO_SET):
            Setting().set(key, 'false')
            self.assertFalse(Setting().get(key))
            Setting().set(key, 'true')
            self.assertTrue(Setting().get(key))
            with six.assertRaisesRegex(self, ValidationException,
                                       'must be a boolean'):
                Setting().set(key, 'not valid')
        testExtraVal = json.dumps({'images': ['label']})
        for key in (constants.PluginSettings.LARGE_IMAGE_SHOW_EXTRA_PUBLIC,
                    constants.PluginSettings.LARGE_IMAGE_SHOW_EXTRA,
                    constants.PluginSettings.LARGE_IMAGE_SHOW_EXTRA_ADMIN):
            Setting().set(key, '')
            self.assertEqual(Setting().get(key), '')
            Setting().set(key, testExtraVal)
            self.assertEqual(Setting().get(key), testExtraVal)
            with six.assertRaisesRegex(self, ValidationException,
                                       'must be a JSON'):
                Setting().set(key, 'not valid')
            with six.assertRaisesRegex(self, ValidationException,
                                       'must be a JSON'):
                Setting().set(key, '[1]')
        Setting().set(
            constants.PluginSettings.LARGE_IMAGE_DEFAULT_VIEWER, 'geojs')
        self.assertEqual(Setting().get(
            constants.PluginSettings.LARGE_IMAGE_DEFAULT_VIEWER), 'geojs')
        with six.assertRaisesRegex(self, ValidationException,
                                   'must be a non-negative integer'):
            Setting().set(
                constants.PluginSettings.LARGE_IMAGE_MAX_THUMBNAIL_FILES, -1)
        Setting().set(
            constants.PluginSettings.LARGE_IMAGE_MAX_THUMBNAIL_FILES, 5)
        self.assertEqual(Setting().get(
            constants.PluginSettings.LARGE_IMAGE_MAX_THUMBNAIL_FILES), 5)
        with six.assertRaisesRegex(self, ValidationException,
                                   'must be a non-negative integer'):
            Setting().set(
                constants.PluginSettings.LARGE_IMAGE_MAX_SMALL_IMAGE_SIZE, -1)
        Setting().set(
            constants.PluginSettings.LARGE_IMAGE_MAX_SMALL_IMAGE_SIZE, 1024)
        self.assertEqual(Setting().get(
            constants.PluginSettings.LARGE_IMAGE_MAX_SMALL_IMAGE_SIZE), 1024)
        # Test the large_image/settings end point
        resp = self.request(path='/large_image/settings', user=None)
        self.assertStatusOk(resp)
        settings = resp.json
        # The values were set earlier
        self.assertEqual(settings[
            constants.PluginSettings.LARGE_IMAGE_DEFAULT_VIEWER], 'geojs')
        self.assertEqual(settings[
            constants.PluginSettings.LARGE_IMAGE_SHOW_VIEWER], True)
        self.assertEqual(settings[
            constants.PluginSettings.LARGE_IMAGE_SHOW_THUMBNAILS], True)
        self.assertEqual(settings[
            constants.PluginSettings.LARGE_IMAGE_SHOW_EXTRA_PUBLIC], testExtraVal)
        self.assertEqual(settings[
            constants.PluginSettings.LARGE_IMAGE_SHOW_EXTRA], testExtraVal)
        self.assertEqual(settings[
            constants.PluginSettings.LARGE_IMAGE_SHOW_EXTRA_ADMIN], testExtraVal)
        self.assertEqual(settings[
            constants.PluginSettings.LARGE_IMAGE_AUTO_SET], True)
        self.assertEqual(settings[
            constants.PluginSettings.LARGE_IMAGE_MAX_THUMBNAIL_FILES], 5)
        self.assertEqual(settings[
            constants.PluginSettings.LARGE_IMAGE_MAX_SMALL_IMAGE_SIZE], 1024)

    def testThumbnailFileJob(self):
        from girder.plugins.large_image.models.image_item import ImageItem

        # Create files via a job
        file = self._uploadFile(os.path.join(
            os.environ['LARGE_IMAGE_DATA'], 'sample_image.ptif'))
        itemId = str(file['itemId'])

        # We should report zero thumbnails
        item = Item().load(itemId, user=self.admin)
        present, removed = ImageItem().removeThumbnailFiles(item, keep=10)
        self.assertEqual(present, 0)

        # Test PUT thumbnails
        resp = self.request(method='PUT', path='/large_image/thumbnails',
                            user=self.user)
        self.assertStatus(resp, 403)
        resp = self.request(method='PUT', path='/large_image/thumbnails',
                            user=self.admin)
        self.assertStatus(resp, 400)
        self.assertIn('spec', resp.json['message'])
        self.assertIn('is required', resp.json['message'])
        resp = self.request(
            method='PUT', path='/large_image/thumbnails', user=self.admin,
            params={'spec': json.dumps({})})
        self.assertStatus(resp, 400)
        self.assertIn('must be a JSON list', resp.json['message'])

        # Run a job to create two sizes of thumbnails
        self.assertTrue(self._createThumbnails([
            {'width': 160, 'height': 100},
            {'encoding': 'PNG'}
        ]))
        # We should report two thumbnails
        present, removed = ImageItem().removeThumbnailFiles(item, keep=10)
        self.assertEqual(present, 2)

        # Run a job to create two sizes of thumbnails, one different than
        # before
        self.assertTrue(self._createThumbnails([
            {'width': 160, 'height': 100},
            {'width': 160, 'height': 160},
        ]))
        # We should report three thumbnails
        present, removed = ImageItem().removeThumbnailFiles(item, keep=10)
        self.assertEqual(present, 3)

        # Asking for a bad thumbnail specification should just do nothing
        self.assertFalse(self._createThumbnails(['not a dictionary']))
        present, removed = ImageItem().removeThumbnailFiles(item, keep=10)
        self.assertEqual(present, 3)

        # Test GET thumbnails
        resp = self.request(path='/large_image/thumbnails', user=self.user)
        self.assertStatus(resp, 403)
        resp = self.request(
            path='/large_image/thumbnails', user=self.admin,
            params={'spec': json.dumps({})})
        self.assertStatus(resp, 400)
        self.assertIn('must be a JSON list', resp.json['message'])
        resp = self.request(path='/large_image/thumbnails', user=self.admin)
        self.assertStatusOk(resp)
        self.assertEqual(resp.json, 3)
        resp = self.request(
            path='/large_image/thumbnails', user=self.admin,
            params={'spec': json.dumps([{'width': 160, 'height': 100}])})
        self.assertStatusOk(resp)
        self.assertEqual(resp.json, 1)

        # Test DELETE thumbnails
        resp = self.request(method='DELETE', path='/large_image/thumbnails',
                            user=self.user)
        self.assertStatus(resp, 403)
        resp = self.request(
            method='DELETE', path='/large_image/thumbnails', user=self.admin,
            params={'spec': json.dumps({})})
        self.assertStatus(resp, 400)
        self.assertIn('must be a JSON list', resp.json['message'])

        # Delete one set of thumbnails
        resp = self.request(
            method='DELETE', path='/large_image/thumbnails', user=self.admin,
            params={'spec': json.dumps([{'encoding': 'PNG'}])})
        self.assertStatusOk(resp)
        present, removed = ImageItem().removeThumbnailFiles(item, keep=10)
        self.assertEqual(present, 2)

        # Try to delete some that don't exist
        resp = self.request(
            method='DELETE', path='/large_image/thumbnails', user=self.admin,
            params={'spec': json.dumps([{'width': 200, 'height': 200}])})
        self.assertStatusOk(resp)
        present, removed = ImageItem().removeThumbnailFiles(item, keep=10)
        self.assertEqual(present, 2)

        # Delete them all
        resp = self.request(
            method='DELETE', path='/large_image/thumbnails', user=self.admin)
        self.assertStatusOk(resp)
        present, removed = ImageItem().removeThumbnailFiles(item, keep=10)
        self.assertEqual(present, 0)

        # We should be able to cancel a job
        slowList = [
            {'width': 1600, 'height': 1000},
            {'width': 3200, 'height': 2000},
            {'width': 1600, 'height': 1002},
            {'width': 1600, 'height': 1003},
            {'width': 1600, 'height': 1004},
        ]
        self.assertEqual(self._createThumbnails(slowList, cancel=True),
                         'canceled')
        present, removed = ImageItem().removeThumbnailFiles(item, keep=10)
        self.assertLess(present, 3 + len(slowList))

    def testDeleteIncompleteTile(self):
        from girder.plugins.jobs.constants import JobStatus
        from girder.plugins.jobs.models.job import Job
        from girder.plugins.worker import CustomJobStatus

        # Test the large_image/settings end point
        resp = self.request(
            method='DELETE', path='/large_image/tiles/incomplete',
            user=self.user)
        self.assertStatus(resp, 403)
        resp = self.request(
            method='DELETE', path='/large_image/tiles/incomplete',
            user=self.admin)
        self.assertStatusOk(resp)
        results = resp.json
        self.assertEqual(results['removed'], 0)

        file = self._uploadFile(os.path.join(
            os.path.dirname(__file__), 'test_files', 'yb10kx5k.png'))
        itemId = str(file['itemId'])
        # Use a simulated cherrypy request, as it won't complete properly
        resp = self.request(
            method='POST', path='/item/%s/tiles' % itemId, user=self.admin)
        resp = self.request(
            method='DELETE', path='/large_image/tiles/incomplete',
            user=self.admin)
        self.assertStatusOk(resp)
        results = resp.json
        self.assertEqual(results['removed'], 1)

        def preventCancel(evt):
            job = evt.info['job']
            params = evt.info['params']
            if (params.get('status') and
                    params.get('status') != job['status'] and
                    params['status'] in (JobStatus.CANCELED, CustomJobStatus.CANCELING)):
                evt.preventDefault()

        # Prevent a job from cancelling
        events.bind('jobs.job.update', 'testDeleteIncompleteTile', preventCancel)
        # Create a job and mark it as running
        resp = self.request(
            method='POST', path='/item/%s/tiles' % itemId, user=self.admin)
        job = Job().load(id=resp.json['_id'], force=True)
        Job().updateJob(job, status=JobStatus.RUNNING)

        resp = self.request(
            method='DELETE', path='/large_image/tiles/incomplete',
            user=self.admin)
        events.unbind('jobs.job.update', 'testDeleteIncompleteTile')
        self.assertStatusOk(resp)
        results = resp.json
        self.assertEqual(results['removed'], 0)
        self.assertIn('could not be canceled', results['message'])
        # Now we should be able to cancel the job
        resp = self.request(
            method='DELETE', path='/large_image/tiles/incomplete',
            user=self.admin)
        self.assertStatusOk(resp)
        results = resp.json
        self.assertEqual(results['removed'], 1)

    def testAssociateImageCaching(self):
        file = self._uploadFile(os.path.join(
            os.environ['LARGE_IMAGE_DATA'], 'sample_image.ptif'))
        itemId = str(file['itemId'])
        resp = self.request(path='/item/%s/tiles/images/label' % itemId,
                            user=self.admin, isJson=False)
        self.assertStatusOk(resp)
        # Test GET associated_images
        resp = self.request(path='/large_image/associated_images', user=self.user)
        self.assertStatus(resp, 403)
        resp = self.request(path='/large_image/associated_images', user=self.admin)
        self.assertStatusOk(resp)
        self.assertEqual(resp.json, 1)
        # Test DELETE associated_images
        resp = self.request(
            method='DELETE', path='/large_image/associated_images', user=self.user)
        self.assertStatus(resp, 403)
        resp = self.request(
            method='DELETE', path='/large_image/associated_images', user=self.admin)
        self.assertStatusOk(resp)
        self.assertEqual(resp.json, 1)
        resp = self.request(path='/large_image/associated_images', user=self.admin)
        self.assertStatusOk(resp)
        self.assertEqual(resp.json, 0)
