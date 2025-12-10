from django.db import models

# Create your models here.
class KanoodleBoard(models.Model):
    name = models.CharField(max_length=100)
    width = models.IntegerField(default=5)
    height = models.IntegerField(default=11)

    def __str__(self):
        return str(self.name)

class Piece(models.Model):
    name = models.CharField(max_length=100, unique=True)
    shapeData = models.JSONField()
    color = models.CharField(max_length=7, default='#999999')

    def __str__(self):
        return str(self.name)

class PyramidBoard(models.Model):
    """Represents a pyramid puzzle configuration"""
    name = models.CharField(max_length=100, default="5-Level Pyramid")
    levels = models.IntegerField(default=5)

    def __str__(self):
        return f"{self.name} ({self.levels} levels)"

class partialSolution(models.Model):
    board = models.ForeignKey(KanoodleBoard, on_delete=models.CASCADE, null=True, blank=True)
    pyramid = models.ForeignKey(PyramidBoard, on_delete=models.CASCADE, null=True, blank=True)
    state_data = models.JSONField(default=dict)
    
    def __str__(self):
        if self.board:
            return f"Solution for {self.board.name} ({self.pk})"
        elif self.pyramid:
            return f"Solution for {self.pyramid.name} ({self.pk})"
        return f"Solution ({self.pk})"


class PyramidSolution(models.Model):
    """Stores 3D pyramid solver sessions"""
    session_key = models.CharField(max_length=100, db_index=True, unique=True)
    pyramid = models.ForeignKey(PyramidBoard, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    partial_board = models.JSONField(default=dict, help_text="Initial board state")
    solutions_data = models.JSONField(default=list, help_text="All found solutions")
    solution_count = models.IntegerField(default=0)
    exhausted = models.BooleanField(default=False)
    timed_out = models.BooleanField(default=False)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Pyramid Solution {self.session_key} - {self.solution_count} solutions"