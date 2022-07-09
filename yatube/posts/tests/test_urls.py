from http import HTTPStatus

from django.contrib.auth import get_user_model
from django.test import TestCase, Client
from django.urls import reverse

from ..models import Group, Post

User = get_user_model()


class PostURLTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.post = Post.objects.create(
            author=User.objects.create_user(username='auth'),
            text='Тестовый пост'
        )

        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test_slug',
            description='Тестовое описание'
        )

    def setUp(self):
        self.guest_client = Client()
        self.user = User.objects.create_user(username='NoName')
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)

    def test_pages_exists_at_desired_location(self):
        """Страницы доступны неавторизованному пользователю."""
        url_names = (
            '/',
            '/group/test_slug/'
        )
        for adress in url_names:
            with self.subTest():
                response = self.guest_client.get(adress)
                self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_create_url_exists_at_desired_location(self):
        """Страница create доступна авторизованному пользователю."""
        response = self.authorized_client.get('/create/')
        self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_posts_urls_uses_correct_template(self):
        """URL-адрес использует соответствующий шаблон."""
        templates_url_names = {
            '/': 'posts/index.html',
            '/group/test_slug/': 'posts/group_list.html',
            '/create/': 'posts/create_post.html',
            '/profile/auth/': 'posts/profile.html',
            '/posts/1/': 'posts/post_detail.html'

        }
        for address, template in templates_url_names.items():
            with self.subTest(address=address):
                response = self.authorized_client.get(address)
                self.assertTemplateUsed(response, template)

    def test_404_url_exists_at_desired_location(self):
        """запрос к несуществующей странице вернёт ошибку 404."""
        response = self.guest_client.get('/group/general/')
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

    def test_posts_id_detail_url_exists_at_desired_location_author(self):
        """Страница /posts/posts_id доступна автору"""
        response = self.authorized_client.get('/posts/1/edit')
        self.assertEqual(response.status_code, HTTPStatus.MOVED_PERMANENTLY)

    def test_create_url_exists_at_desired_location(self):
        """Страница /create/ доступна любому пользователю."""
        response = self.guest_client.get('/create/')
        self.assertEqual(response.status_code, HTTPStatus.FOUND)

    def test_unexisting_url_exists_at_desired_location(self):
        """Несуществующая страница"""
        response = self.guest_client.get('/unexisting/')
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

    def test_post_edit_url_redirect_anonymous(self):
        """Страница /post_id/edit перенаправляет анонимного пользователя."""
        response = self.guest_client.get(reverse('posts:post_edit', kwargs={
            'post_id': PostURLTests.post.id}), follow=True)
        self.assertRedirects(response, '/auth/login/?next=/posts/1/edit/')

    def test_post_create_url_redirect_anonymous(self):
        """Страница /posts/create/ перенаправляет анонимного пользователя. """
        response = self.guest_client.get(
            reverse('posts:post_create'), follow=True)
        self.assertRedirects(response, ('/auth/login/?next=/create/'))


class StaticURLTests(TestCase):
    def setUp(self):
        self.guest_client = Client()

    def test_homepage(self):
        response = self.guest_client.get('/')
        self.assertEqual(response.status_code, HTTPStatus.OK)
