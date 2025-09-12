import pytest
from landifys.services import interactions
from landifys.models import User, Post, Reaction


@pytest.fixture
def reaction_setup():
    user = User.objects.create_user(username='user')
    post_owner = User.objects.create_user(username='post_owner')
    post = Post.objects.create(user=post_owner, title="Test Post")
    return user, post


@pytest.mark.django_db
@pytest.mark.step_log
def test_process_post_reaction_flow(reaction_setup, log_step):
    """
    KỊCH BẢN: Thành công
    Kiểm tra toàn bộ luồng: tạo mới -> cập nhật -> xóa cảm xúc.
    """
    user, post = reaction_setup

    log_step("--- Lượt 1: Tạo mới (Like) ---")
    log_step("ACT: Người dùng 'like' bài đăng.")
    status1, reaction1 = interactions.process_post_reaction(user=user, post=post, reaction_type='like')

    log_step("ASSERT: Trạng thái là 'created'.")
    assert status1 == 'created'
    log_step("ASSERT: Một bản ghi Reaction 'like' được tạo.")
    assert Reaction.objects.count() == 1
    assert Reaction.objects.first().type == 'like'

    log_step("--- Lượt 2: Cập nhật (Love) ---")
    log_step("ACT: Người dùng đổi từ 'like' sang 'love'.")
    status2, reaction2 = interactions.process_post_reaction(user=user, post=post, reaction_type='love')

    log_step("ASSERT: Trạng thái là 'updated'.")
    assert status2 == 'updated'
    log_step("ASSERT: Vẫn chỉ có 1 bản ghi Reaction, nhưng type đã đổi thành 'love'.")
    assert Reaction.objects.count() == 1
    assert Reaction.objects.first().type == 'love'

    log_step("--- Lượt 3: Xóa (Love) ---")
    log_step("ACT: Người dùng bấm lại vào 'love'.")
    status3, reaction3 = interactions.process_post_reaction(user=user, post=post, reaction_type='love')

    log_step("ASSERT: Trạng thái là 'deleted'.")
    assert status3 == 'deleted'
    log_step("ASSERT: Không còn bản ghi Reaction nào trong CSDL.")
    assert Reaction.objects.count() == 0
    log_step("=> PASSED!")