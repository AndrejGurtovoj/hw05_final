import shutil
import tempfile

from django.contrib.auth import get_user_model
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.conf import settings
from django.core.cache import cache
from django import forms
from django.core.files.uploadedfile import SimpleUploadedFile

from ..models import Group, Post, Comment, Follow

User = get_user_model()

TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


NUM_POSTS = 10


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostViewsTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='auth')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test-slug',
            description='Тестовое описание',
        )
        cls.post = Post.objects.create(
            text='Тестовый заголовок',
            author=cls.user,
            group=cls.group,
        )
        cls.new_group = Group.objects.create(
            title='Новая группа',
            slug='test-slug_new',
            description='Новое описание',
        )
        small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x02\x00'
            b'\x01\x00\x80\x00\x00\x00\x00\x00'
            b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
            b'\x00\x00\x00\x2C\x00\x00\x00\x00'
            b'\x02\x00\x01\x00\x00\x02\x02\x0C'
            b'\x0A\x00\x3B'
        )
        uploaded = SimpleUploadedFile(
            name='small.gif',
            content=small_gif,
            content_type='image/gif'
        )
        for i in range(1, 10):
            cls.post = Post.objects.create(
                text='Тестовый текст ' + str(i),
                author=cls.user,
                group=cls.group,
                image=uploaded
            )

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.guest_client = Client()
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)

        cache.clear()

    def post_response_context(self, response):
        """Проверяем Context в двух тестах"""
        form_fields = {
            'text': forms.fields.CharField,
            'group': forms.fields.ChoiceField,
        }
        for value, expected in form_fields.items():
            with self.subTest(value=value):
                form_field = response.context.get('form').fields.get(value)
                self.assertIsInstance(form_field, expected)

    def test_cache_index(self):
        """Тест кэш index"""
        get_index = self.authorized_client.get(reverse('posts:index'))
        post4cache = Post.objects.get(pk=1)
        post4cache.text = 'Кеш текст'
        post4cache.save()
        test1 = self.authorized_client.get(reverse('posts:index'))
        self.assertEqual(get_index.content, test1.content)
        cache.clear()
        test2 = self.authorized_client.get(reverse('posts:index'))
        self.assertNotEqual(get_index.content, test2.content)

    def test_pages_uses_correct_template(self):
        """URL-адрес использует соответствующий шаблон."""
        templates_pages_names = {
            reverse('posts:index'): 'posts/index.html',
            reverse(
                'posts:group_list',
                kwargs={'slug': self.group.slug}
            ): 'posts/group_list.html',
            reverse(
                'posts:profile',
                kwargs={'username': self.post.author.username}
            ): 'posts/profile.html',
            reverse(
                'posts:post_detail',
                kwargs={'post_id': self.post.id}
            ): 'posts/post_detail.html',
            reverse('posts:post_create'): 'posts/create_post.html',
            reverse(
                'posts:post_edit',
                kwargs={'post_id': 1}
            ): 'posts/create_post.html'
        }
        for reverse_name, template in templates_pages_names.items():
            with self.subTest(reverse_name=reverse_name):
                response = self.authorized_client.get(reverse_name)
                self.assertTemplateUsed(response, template)

    def test_index_page_show_correct_context(self):
        """Шаблон index сформирован с правильным контекстом."""
        response = self.authorized_client.get(reverse('posts:index'))
        self.assertEqual(
            response.context['page_obj'].object_list[0], self.post)
        self.assertContains(response, 'image')

    def test_group_list_show_correct_context(self):
        """Шаблон group_list сформирован с правильным контекстом."""
        response = self.authorized_client.get(
            reverse(
                'posts:group_list',
                kwargs={'slug': self.group.slug}
            )
        )
        test_group_title = response.context.get('group').title
        test_group = response.context.get('group').description
        self.assertEqual(test_group_title, 'Тестовая группа')
        self.assertEqual(test_group, self.group.description)
        self.assertContains(response, 'image')

    def test_profile_show_correct_context(self):
        """Шаблон profile сформирован с правильным контекстом."""
        response = self.authorized_client.get(
            reverse('posts:profile',
                    kwargs={'username': self.user})
        )
        test_author = response.context.get('author')
        self.assertEqual(test_author, self.post.author)
        self.assertContains(response, 'image')

    def test_post_detail_show_correct_context(self):
        """Шаблон post_detail сформирован с правильным контекстом."""
        response = self.client.get(reverse(
            'posts:post_detail',
            kwargs={'post_id': self.post.id})
        )
        self.assertEqual(response.context.get('post'), self.post)
        self.assertContains(response, 'image')

    def test_create_post_show_correct_context(self):
        """Шаблон create_post сформирован с правильным контекстом."""
        response = (self.authorized_client.get(reverse('posts:post_create')))
        form_fields = {
            'text': forms.fields.CharField,
            'group': forms.fields.ChoiceField,
        }
        for value, expected in form_fields.items():
            with self.subTest(value=value):
                form_field = response.context.get('form').fields.get(value)
                self.assertIsInstance(form_field, expected)

    def test_post_edit_page_show_correct_context(self):
        """Шаблон post_edit сформирован с правильным контекстом."""
        response = self.authorized_client.get(
            reverse('posts:post_edit', kwargs={'post_id': self.post.pk}))
        is_edit = response.context['is_edit']
        self.post_response_context(response)
        self.assertTrue(is_edit)

    def test_check_post_on_create(self):
        """ Проверяем, что при создании поста с группой
        этот пост появляется на главной странице,
        на странице группы, на старнице профайла. """
        pages = [
            reverse('posts:index'),
            reverse('posts:group_list', kwargs={'slug': self.group.slug}),
            reverse('posts:profile', kwargs={'username': self.user.username})
        ]
        for page in pages:
            with self.subTest(page=page):
                response = self.authorized_client.get(page)
                self.assertEqual(response.context.get(
                    'page_obj')[0], self.post)

    def test_comment_post_auth_user(self):
        comment = Comment.objects.create(
            text='Коментарий', author=self.user, post_id=self.post.id)
        response = (self.client.post(
            reverse('posts:add_comment', kwargs={'post_id': self.post.id})))
        response = (self.client.get(
            reverse('posts:post_detail', kwargs={'post_id': self.post.id})))
        self.assertContains(response, comment)
        self.client.logout()
        response = (self.client.post(
            reverse('posts:add_comment', kwargs={'post_id': self.post.id})))
        self.assertRedirects(response, reverse(
            'users:login') + '?next=' + reverse(
                'posts:add_comment',
            kwargs={'post_id': self.post.id}))

    def test_group_post(self):
        """ Проверка на ошибочное попадание поста не в ту группу. """
        response = self.authorized_client.get(
            reverse(
                'posts:group_list',
                kwargs={'slug': self.new_group.slug}
            )
        )
        self.assertEqual(response.context['page_obj'].paginator.count, 0)


class PiginatorViewsTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='auth')
        cls.group = Group.objects.create(
            title='Тестовая группа_2',
            slug='test_slug',
            description='Тестовое_описание_2'
        )
        for post_text in range(13):
            cls.posts = Post.objects.create(
                author=cls.user,
                group=cls.group,
                text=f'{post_text} Тестовый текст'
            )

    def setUp(self):
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)

    def test_paginator_correct(self):
        """ Проверка паджинатора. """
        templates = [
            reverse('posts:index'),
            reverse('posts:group_list', kwargs={'slug': self.group.slug}),
            reverse('posts:profile',
                    kwargs={'username': self.user.username})
        ]
        for num in range(len(templates)):
            with self.subTest(templates=templates[num]):
                response = self.authorized_client.get(templates[num])
                self.assertEqual(len(response.context['page_obj']), NUM_POSTS)

    def test_profile_follow(self):
        """Проверяем что пользователь может подписаться."""
        follow_count = Follow.objects.count()
        username = self.user.username
        self.authorized_client.get(reverse(
            'posts:profile_follow',
            kwargs={'username': username}
        ))
        self.assertEqual(Follow.objects.count(), follow_count)

    def test_profile_unfollow(self):
        """Проверяем что пользователь может отписаться."""
        follow_count = Follow.objects.count()
        username = self.user.username
        self.authorized_client.get(reverse(
            'posts:profile_unfollow',
            kwargs={'username': username}
        ))
        self.assertEqual(Follow.objects.count(), follow_count)
